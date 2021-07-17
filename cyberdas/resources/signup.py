import json
from os import path

import falcon
from falcon.media.validators import jsonschema

from cyberdas.models import User, Faculty


class Signup(object):

    auth = {'disabled': 1}

    with open(path.abspath('cyberdas/static/signup_schema.json'), 'r') as f:
        signup_schema = json.load(f)

    def __init__(self, mail_service, pass_checker, testing = False):
        self.mail = mail_service
        self.pass_checker = pass_checker
        self._testing = testing

    @jsonschema.validate(signup_schema)
    def on_post(self, req, resp):
        '''
        Обрабатывает запрос на регистрацию, и, в случае корректности данных,
        регистрирует пользователя и отправляет письмо для подтверждения
        адреса почты.

        Требует JSON во входящем потоке.
        '''
        dbses = req.context.session
        log = req.context.logger

        # Получаем данные из входящего JSONа
        data = req.get_media()

        # Проверка, что адрес почты не занят
        user = dbses.query(User).filter_by(email = data['email']).first()
        if user is not None:
            log.debug('[ЗАНЯТЫЙ АДРЕС ПОЧТЫ] email %s' % data['email'])
            raise falcon.HTTPBadRequest(
                description = 'Такой адрес почты уже занят.'
            )

        # Проверка, что указанный факультет существует
        faculty = dbses.query(Faculty).filter_by(name = data['faculty']).first()
        if faculty is None:
            log.debug('[НЕСУЩЕСТВУЮЩИЙ ФАКУЛЬТЕТ] email %s' % data['email'])
            raise falcon.HTTPBadRequest(
                description = 'Такой факультет не существует.'
            )

        # Проверка сложности пароля
        suggestions = self.pass_checker.check(data['password'], data['email'])
        if len(suggestions) > 0:
            log.debug('[СЛАБЫЙ ПАРОЛЬ] email %s' % data['email'])
            raise falcon.HTTPBadRequest(
                description = 'Слабый пароль. %s' % ' '.join(suggestions)
            )

        # Добавление пользователя в базу данных
        newUser = User(
            email = data['email'], password = data['password'],
            name = data['name'], surname = data['surname'],
            patronymic = (data['patronymic'] if 'patronymic' in data.keys()
                          else None),
            faculty_id = faculty.id, email_verified = False, verified = False
        )
        dbses.add(newUser)
        log.info('[НОВЫЙ ПОЛЬЗОВАТЕЛЬ] email %s' % data['email'])

        # Отправка письма с подтверждением адреса почты
        verify_url = self.mail.send_verification(req, data['email'])
        log.debug('[ОТПРАВЛЕН EMAIL] email %s, link %s' % (data['email'],
                                                           verify_url))

        resp.status = falcon.HTTP_200
