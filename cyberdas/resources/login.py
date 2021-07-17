import json
import secrets
from os import path
from datetime import datetime, timedelta

import falcon
from falcon.media.validators import jsonschema

from cyberdas.models import User, Session


class Login(object):

    auth = {'disabled': 1}

    with open(path.abspath('cyberdas/static/login_schema.json'), 'r') as f:
        login_schema = json.load(f)

    def __init__(self, cfg):
        self.ses_len = int(cfg['internal']['session.length'])

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

        # Генерируем безопасные токены для идентификатора сессии и csrf-токена
        sid = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)

        # Добавляем новую сессию в базу данных
        newSession = Session(
            sid = sid, uid = user.id, csrf_token = csrf_token,
            user_agent = req.user_agent, ip = req.access_route[-1],
            expires = datetime.now() + timedelta(seconds = self.ses_len)
        )
        dbses.add(newSession)
        log.info('[НОВАЯ СЕССИЯ] sid %s, uid %s, csrf %s' % (sid, user.id, csrf_token)) # noqa

        # Возвращаем пользователю сессионные куки и csrf-токен
        resp.set_cookie(
            name = 'SESSIONID', value = sid, max_age = self.ses_len,
            secure = True, http_only = True, same_site = 'Strict'
        )
        resp.set_header(name = 'XCSRF-Token', value = csrf_token)

        resp.status = falcon.HTTP_200
