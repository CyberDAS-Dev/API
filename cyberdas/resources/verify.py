import falcon

from cyberdas.models import User


class Verify(object):

    auth = {'disabled': 1}

    def __init__(self, mail):
        self.mail = mail

    def on_get(self, req, resp):
        '''
        Сверяет приходящий от пользователя почтовый токен и верифицирует
        его адрес почты.

        Требует параметра `token` в query входящего запроса. Получает его в
        query, хоть это и не очень хорошая практика, так как переадрессация
        из письма возможна только GET-методом.

        Если в токене был зашифрован параметр переадресации, то возвращает
        HTTP 303 See Other.
        '''
        dbses = req.context.session
        log = req.context.logger

        token = req.get_param('token', required = True)

        deciphered = self.mail.confirm_token(token)
        if deciphered is False:
            raise falcon.HTTPUnauthorized
        user = dbses.query(User).filter_by(email = deciphered['email']).first()
        user.email_verified = True
        log.debug("[ПОЧТА ПОДТВЕРЖДЕНА] email %s" % deciphered['email'])

        if 'redirect' in deciphered:
            raise falcon.HTTPSeeOther(location = deciphered['redirect'])
        else:
            resp.status = falcon.HTTP_200
