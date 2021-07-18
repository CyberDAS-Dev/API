import falcon


class Refresh(object):

    def __init__(self, manager):
        self.manager = manager

    def on_get(self, req, resp):
        '''
        Обрабатывает запрос от авторизованного пользователя на продление
        сессии по предъявлению сессионного куки.
        '''
        # Устанавливаем новое время окончания действия сессии - равное
        # стандартной продолжительности сессии, отсчитываемой с текущего момента
        s_cookie = self.manager.refresh_session(req)

        # Возвращаем пользователю куки с новой продолжительностью действия
        resp.set_cookie(**s_cookie)

        resp.status = falcon.HTTP_200
