import json
from os import path
from datetime import datetime

import falcon
from falcon.media.validators import jsonschema

from cyberdas.models import User
from cyberdas.services import TransactionMailFactory
from cyberdas.services import SessionManager


mail_args = {
    'sender': 'signup',
    'subject': 'Вход в аккаунт на CyberDAS',
    'template': 'login',
    'transaction': 'account/login/validate',
    'expires': True
}


class Sender:

    auth = {'disabled': 1}

    with open(path.abspath('cyberdas/static/login_schema.json'), 'r') as f:
        login_schema = json.load(f)

    def __init__(self, mail_factory: TransactionMailFactory):
        self.mail = mail_factory.new(**mail_args)

    # для протокола: jsonschema ловит некорректные эмэйлы и выкидывает 400-ые
    @jsonschema.validate(login_schema)
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        '''
        Отправляет письмо для логина.
        Позволяет отказаться от опасного хранения паролей на сервере и
        использовать только эмэйл для аутентификации.

        Принимает JSON с адресом почты.
        '''
        dbses = req.context.session
        log = req.context.logger

        # Получаем пользовательские данные
        data = req.get_media()

        # Убираем пробелы
        data['email'] = data['email'].strip()

        # Проверка, что пользователь зарегистрирован
        user = dbses.query(User).filter_by(email = data['email']).first()
        if user is None:
            log.debug('[НЕСУЩЕСТВУЮЩИЙ ЛОГИН] email %s' % data['email'])
            raise falcon.HTTPForbidden(
                description = 'Такой адрес почты не зарегистрирован'
            )

        # Для удобства Validator'а добавляем в данные uid
        data['uid'] = user.id

        self.mail.send(req, data['email'], data)
        log.info('[ПИСЬМО][ЛОГИН] email %s' % data['email'])
        resp.status = falcon.HTTP_202


class Validator:

    auth = {'disabled': 1}

    def __init__(self,
                 mail_factory: TransactionMailFactory,
                 ses_manager: SessionManager):
        self.mail = mail_factory.new(**mail_args)
        self.ses_manager = ses_manager

    def on_get(self, req: falcon.Request, resp: falcon.Response):
        '''
        Создает новую сессию в БД и возвращает куки.

        Принимает подписанный токен с данными для логина.
        '''
        dbses = req.context.session
        log = req.context.logger

        # Получаем токен от пользователя
        token = req.get_param('token', required = True)

        # Расшифровываем его и убеждаемся в его валидности
        data = self.mail.confirm_token(token)
        if data is False:
            raise falcon.HTTPForbidden(
                description = 'Неверный или просроченный токен'
            )

        # Создание новой сессии
        session_data = {
            'uid': data['uid'], 'user_agent': req.user_agent,
            'ip': req.get_header('X-Real-IP') or req.access_route[-1]
        }
        cookie, csrf_token = self.ses_manager.start(dbses, **session_data)

        user = dbses.query(User).filter_by(id = data['uid']).first()
        user.last_session = datetime.now()

        resp.set_cookie(**cookie)
        resp.set_header(name = 'X-CSRF-Token', value = csrf_token)

        log.info('[НОВАЯ СЕССИЯ] uid {uid} ip {ip}'.format(**session_data))
        resp.status = falcon.HTTP_201
