from datetime import timedelta, datetime

import falcon

from cyberdas.models import Session


class Refresh(object):

    def __init__(self, cfg):
        self.ses_len = int(cfg['internal']['session.length'])

    def on_get(self, req, resp):
        '''
        Обрабатывает запрос от авторизованного пользователя на продление
        сессии по предъявлению сессионного куки.
        '''
        dbses = req.context.session
        log = req.context.logger
        user = req.context.user

        # Устанавливаем новое время окончания действия сессии - равное
        # стандартной продолжительности сессии, отсчитываемой с текущего момента
        now = datetime.now()
        session = dbses.query(Session).filter_by(sid = user['sid'])
        session.update({Session.expires: now + timedelta(seconds = self.ses_len)}) # noqa

        # Возвращаем пользователю куки с новой продолжительностью действия
        resp.set_cookie(
            name = 'SESSIONID', value = user['sid'], max_age = self.ses_len,
            secure = True, http_only = True, same_site = 'Strict'
        )
        log.debug("[ПРОДЛЕНА СЕССИЯ] sid %s, uid %s" % (user['sid'], user['uid'])) # noqa

        resp.status = falcon.HTTP_200
