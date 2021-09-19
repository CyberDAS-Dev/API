import json
from os import path

from jsonschema import validate
from jsonschema import draft7_format_checker
from jsonschema.exceptions import ValidationError
import falcon

from cyberdas.models import User
from cyberdas.services.mail import Mail
from cyberdas.config import get_cfg

with open(path.abspath('cyberdas/static/login_schema.json'), 'r') as f:
    login_schema = json.load(f)
    login_schema['additionalProperties'] = True

with open(path.abspath('cyberdas/static/signup_schema.json'), 'r') as f:
    signup_schema = json.load(f)
    # на случай если эндпоинт сам принимает какой-то POST запрос:
    signup_schema['additionalProperties'] = True

cfg = get_cfg()


def _get_or_add_user(req: falcon.Request, data: dict):
    '''
    Функция, которая модифицирует контекст запроса, добавляя в него
    идентификатор пользователя, даже если пользователь не имеет активной сессии.

    Требует персональных данных в запросе. В случае, если пользователь не
    зарегистрирован, то регистрирует его.

    Должна использоваться как хук перед запросом.

    Внимание! Представляет угрозу для безопасности, так как позволяет совершать
    действия за другого пользователя, зная только его адрес почты. Настоятельно
    рекомендуется использовать только на некритичных ресурсах.
    '''
    dbses = req.context.session
    log = req.context.logger

    # Сценарий 1: пользователь уже регистрировался и вводит только эмэйл
    try:
        validate(data, schema = login_schema, format_checker = draft7_format_checker) # noqa
    except ValidationError:
        raise falcon.HTTPUnauthorized()

    # Чистим данные, так как additionalProperties = true
    clean_data = {k: data[k] for k in signup_schema['properties'] if k in data}

    user = dbses.query(User).filter_by(email = data['email']).first()
    if user is not None:
        # Обновляем данные пользователя, если он предоставил более свежие
        for (key, item) in clean_data.items():
            setattr(user, key, item)
        dbses.flush()
        log.info('[QA][ЛОГИН] email %s uid %s' % (data['email'], user.id))
        req.context['user'] = {'uid': user.id}
        return

    # Сценарий 2: пользователь отправил все данные для регистрации
    try:
        validate(data, schema = signup_schema, format_checker = draft7_format_checker) # noqa
    except ValidationError:
        raise falcon.HTTPUnauthorized()

    # При регистрации такого пользователя его нужно отметить галочкой quick
    newUser = User(**clean_data, quick = True)

    dbses.add(newUser)
    dbses.flush()
    log.info('[QA][НОВЫЙ ПОЛЬЗОВАТЕЛЬ] email %s uid %s' % (data['email'], newUser.id)) # noqa
    req.context['user'] = {'uid': newUser.id}


def auth_on_post(req: falcon.Request, resp: falcon.Response, resource, params):
    '''
    Вызывает хук быстрой аутентификации на POST-запросах, когда данные находятся
    в JSON'е.
    '''
    # Если пользователь уже аутентифицировался, ничего не делаем
    if req.context.user is not None:
        return

    # Получаем пользовательские данные и чистим их, т.к они из веб-формы
    data = req.get_media()
    for key, value in data.items():
        if isinstance(value, str):
            data[key] = value.strip()

    _get_or_add_user(req, data)


class auth_on_token:
    '''
    Инициализируемая функция.
    Вызывает хук быстрой аутентификации на GET-запросах, когда данные находятся
    в почтовом токене.

    Аргументы инициализации:
        sender(string, необходим): имя оригинального отправителя почтового
            токена, необходимо для расшифровки токена.

        expires(bool, опционально): флаг, устанавливающий, может ли токен
            просрочиться.
    '''

    def __init__(self, sender, expires = False):
        self.mail = Mail(cfg, sender)
        self.expires = expires

    def __call__(self, req: falcon.Request, resp: falcon.Response, resource, params): # noqa
        # Если пользователь уже аутентифицировался, ничего не делаем
        if req.context.user is not None:
            return

        # Валидируем и распаковываем токен
        token = req.get_param('token', required = True)
        data = self.mail.confirm_token(token, self.expires)
        if data is False:
            raise falcon.HTTPForbidden(
                description = 'Неверный или просроченный токен'
            )

        _get_or_add_user(req, data)
