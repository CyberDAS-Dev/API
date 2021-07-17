import json
from os import path

import falcon
from falcon.media.validators import jsonschema

from cyberdas.models import User


class Resend(object):

    auth = {'disabled': 1}

    with open(path.abspath('cyberdas/static/resend_schema.json'), 'r') as f:
        resend_schema = json.load(f)

    def __init__(self, mail):
        self.mail = mail

    @jsonschema.validate(resend_schema)
    def on_post(self, req, resp):
        '''
        Заново отправляет письмо с токеном для подтверждения адреса почты.

        Требует JSON с адресом почты во входящем потоке.
        '''
        dbses = req.context.session
        log = req.context.logger

        # Получение данных из входящего JSONа
        data = req.get_media()

        # Ищем пользователя с таким адресом почты в базе данных
        user = dbses.query(User).filter_by(email = data['email']).first()

        # Отправляем письмо пользователю, если он существует и неверифицирован
        if user is not None and user.email_verified is False:
            verify_url = self.mail.send_verification(req, data['email'])
            log.debug('[ОТПРАВЛЕН EMAIL] email %s, link %s' % (data['email'],
                                                               verify_url))

        # Маскируем отсутствие пользователя в базе данных, возвращяя HTTP OK
        # и обещая послать письмо в любом случае
        resp.status = falcon.HTTP_200
