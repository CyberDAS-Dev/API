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
        user = req.context.user

        # Удаляем сессию, соответствующую куки, из базы данных
        session = dbses.query(Session).filter_by(sid = user['sid']).first()
        dbses.delete(session)

        # Возвращаем пользователю куки, просрочившиеся в прошлом
        # (это заставит браузер автоматически удалить их)
        resp.set_cookie(
            name = 'SESSIONID', value = user['sid'], max_age = -1,
            secure = True, http_only = True, same_site = 'Strict'
        )
        log.debug("[КОНЕЦ СЕССИИ] sid %s, uid %s" % (user['sid'], user['uid']))

        resp.status = falcon.HTTP_200
