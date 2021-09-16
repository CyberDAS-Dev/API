import falcon

from cyberdas.services import auth_on_post, generate_ott
from cyberdas.config import get_cfg

exp = get_cfg()['internal']['ott.length']


class Ott:

    auth = {'disabled': 1}

    @falcon.before(auth_on_post)
    def on_post(self, req: falcon.Request, resp: falcon.Response):
        '''
        Возвращает краткосрочный токен для совершения одного действия.
        Требует персональных данных в теле запроса.
        '''
        ott = generate_ott(req.context.user)
        req.context.logger.info('[OTT][ВЫДАН] uid %s'
                                % (req.context['user']['uid']))
        resp.media = {'token': ott, 'token_type': 'Bearer', 'expires_in': exp}
        resp.status = falcon.HTTP_201
