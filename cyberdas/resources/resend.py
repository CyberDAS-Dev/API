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

        data = req.get_media()

        user = dbses.query(User).filter_by(email = data['email']).first()
        if user is None:
            resp.status = falcon.HTTP_200
            return
        if user.email_verified is True:
            raise falcon.HTTPForbidden

        self.mail.send_verification(req, data['email'])
        log.debug("[EMAIL-ТОКЕН ПЕРЕОТПРАВЛЕН] email %s" % data['email'])
        resp.status = falcon.HTTP_200
