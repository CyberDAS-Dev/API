import falcon


class Logout(object):

    def __init__(self, manager):
        self.manager = manager

    def on_get(self, req, resp):
        '''
        Обрабатывает запрос от авторизованного пользователя на прекращение
        сессии по предъявлению сессионного куки.
        '''
        # Удаляем сессию, соответствующую данному куки, из базы данных
        cookie_list = self.manager.end_session(req)

        # Возвращаем пользователю куки, просрочившиеся в прошлом
        # (это заставит браузер автоматически удалить их)
        for cookie in cookie_list:
            resp.set_cookie(**cookie)

        resp.status = falcon.HTTP_200
