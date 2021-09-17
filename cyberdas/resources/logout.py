import falcon

from cyberdas.services import SessionManager


class Logout(object):

    def __init__(self, ses_manager: SessionManager):
        self.ses_manager = ses_manager

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        '''
        Обрабатывает запрос от авторизованного пользователя на завершение
        сессии.
        '''
        dbses = req.context.session
        log = req.context.logger
        user = req.context.user

        # Удаляем сессию, соответствующую данному куки, из базы данных
        cookie = self.ses_manager.end(dbses, sid = user['sid'])

        # Возвращаем пользователю куки, просрочившиеся в прошлом
        # (это заставит браузер автоматически удалить их)
        resp.set_cookie(**cookie)

        log.info('[КОНЕЦ СЕССИИ] uid %s ip %s' % (user['uid'], user['ip']))
        resp.status = falcon.HTTP_204
