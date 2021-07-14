import falcon

from cyberdas.models import Session


class Logout(object):

    def on_get(self, req, resp):
        '''
        Обрабатывает запрос от авторизованного пользователя на прекращение
        сессии по предъявлению сессионного куки.
        '''
        dbses = req.context.session
        log = req.context.logger

        try:
            session_cookies = req.get_cookie_values('SESSIONID')
            assert session_cookies is not None
            # Игнорируем все SESSIONID куки в запросе кроме первой
            sid = session_cookies[0]
            session = dbses.query(Session).filter_by(sid = sid).first()
            assert session is not None
        except AssertionError:
            raise falcon.HTTPUnauthorized

        dbses.delete(session)
        resp.set_cookie(
            name = 'SESSIONID', value = sid, max_age = -1,
            secure = True, http_only = True, same_site = 'Strict'
        )
        log.debug("[КОНЕЦ СЕССИИ] sid %s, uid %s" % (sid, session.uid))
        resp.status = falcon.HTTP_200
