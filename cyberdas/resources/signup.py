import json
from os import path

import falcon
from falcon.media.validators import jsonschema

from cyberdas.models import User
from cyberdas.services import TransactionMailFactory


mail_args = {
    'sender': 'signup',
    'subject': 'Регистрация на CyberDAS',
    'template': 'signup',
    'transaction': 'account/signup/validate',
    'expires': True
}


class Sender:

    auth = {'disabled': 1}

    with open(path.abspath('cyberdas/static/signup_schema.json'), 'r') as f:
        signup_schema = json.load(f)

    def __init__(self, mail_factory: TransactionMailFactory):
        self.mail = mail_factory.new(**mail_args)

    # для протокола: jsonschema ловит некорректные эмэйлы и выкидывает 400-ые
    @jsonschema.validate(signup_schema)
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        '''
        Отправляет письмо для регистрации новых пользователей.
        При этом не создает ничего в БД, что позволяет обезопасить себя от
        DoS-аттак.

        Принимает JSON с персональными данными и адресом почты.
        '''
        dbses = req.context.session
        log = req.context.logger

        # Получаем пользовательские данные
        data = req.get_media()

        # Важный пункт - убираем пробелы из пользовательских данных.
        # Многие люди случайно оставляют пробелы когда заполняют веб-формы
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = value.strip()

        # Проверка, что адрес почты не занят
        user = dbses.query(User).filter_by(email = data['email']).first()
        if user is not None:
            log.debug('[ЗАНЯТЫЙ АДРЕС ПОЧТЫ] email %s' % data['email'])
            raise falcon.HTTPForbidden(
                description = 'Такой адрес почты уже занят'
            )

        self.mail.send(req, data['email'], data)
        log.info('[ПИСЬМО][РЕГИСТРАЦИЯ] email %s' % data['email'])
        resp.status = falcon.HTTP_202


class Validator:

    auth = {'disabled': 1}

    def __init__(self, mail_factory: TransactionMailFactory):
        self.mail = mail_factory.new(**mail_args)

    def on_get(self, req: falcon.Request, resp: falcon.Response):
        '''
        Регистрирует в БД новых пользователей.

        Принимает подписанный токен с данными для регистрации.
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

        # Проверка, что адрес почты не занят.
        # Может выглядеть странно, ведь уже была проверка в Sender'е, но нет
        # гарантий, что на ссылку из письма нажмут только один раз.
        user = dbses.query(User).filter_by(email = data['email']).first()
        if user is not None:
            log.debug('[ЗАНЯТЫЙ АДРЕС ПОЧТЫ] email %s' % data['email'])
            raise falcon.HTTPForbidden(
                description = 'Такой адрес почты уже занят'
            )

        # Добавление пользователя в базу данных
        newUser = User(
            email = data['email'],
            name = data['name'], surname = data['surname'],
            patronymic = (data['patronymic'] if 'patronymic' in data.keys()
                          else None),
            faculty_id = data['faculty_id']
        )

        dbses.add(newUser)
        dbses.flush()
        log.info('[НОВЫЙ ПОЛЬЗОВАТЕЛЬ] email %s uid %s' % (data['email'], newUser.id)) # noqa
        resp.status = falcon.HTTP_201
