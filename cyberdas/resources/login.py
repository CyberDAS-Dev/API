import json
from os import path

import falcon
from falcon.media.validators import jsonschema

from cyberdas.models import User


class Login(object):

    auth = {'disabled': 1}

    with open(path.abspath('cyberdas/static/login_schema.json'), 'r') as f:
        login_schema = json.load(f)

    def __init__(self, manager):
        self.manager = manager

    @jsonschema.validate(login_schema)
    def on_post(self, req, resp):
        '''
        Обрабатывает запрос на логин, и, в случае корректности данных,
        выдает пользователю авторизационный куки и CSRF-токен.

        Требует JSON во входящем потоке.
        '''
        dbses = req.context.session
        log = req.context.logger

        # Получение данных из входящего JSONа
        data = req.get_media()

        # Ищем пользователя в базе данных и проверяем корректность данных
        # При этом маскируем отсутствие пользователя или ввод неверного пароля
        user = dbses.query(User).filter_by(email = data['email']).first()
        if user is None:
            raise falcon.HTTPBadRequest
        if data['password'] != user.password:
            log.warning('[НЕВЕРНЫЙ ПАРОЛЬ] email %s', data['email'])
            raise falcon.HTTPBadRequest

        # Создаем новую сессию
        s_cookie, csrf_token = self.manager.start_session(req, user)

        # Возвращаем пользователю сессионные куки и csrf-токен
        resp.set_cookie(**s_cookie)
        resp.set_header(name = 'XCSRF-Token', value = csrf_token)

        # Проверяем наличие параметра remember в query-строке
        remember = req.get_param_as_bool('remember')

        # Выдаем пользователю remember-me куки, если он попросил
        if remember:
            l_cookie = self.manager.start_l_session(req, user, s_cookie)
            resp.set_cookie(**l_cookie)

        resp.status = falcon.HTTP_200
