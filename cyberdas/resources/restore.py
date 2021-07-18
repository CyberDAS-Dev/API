import falcon

from cyberdas.exceptions import SecurityError

class Restore:

    auth = {'disabled': 1}

    def __init__(self, manager):
        self.manager = manager

    def on_get(self, req, resp):
        '''
        Обрабатывает запрос на логин по токену без ввода пароля, в случае
        корректности данных выдает пользователю новый токен и сессионный куки.
        '''
        # Пытаемся продлить сессию
        try:
            l_cookie, s_cookie, csrf = self.manager.continue_session(req)
        except SecurityError as e:
            req.context.logger.error(e)
            raise falcon.HTTPBadRequest
        except Exception as e:
            req.context.logger.info(e)
            raise falcon.HTTPBadRequest

        # Возвращаем пользователю все сессионные куки и csrf-токен
        resp.set_cookie(**l_cookie)
        resp.set_cookie(**s_cookie)
        resp.set_header(name = 'XCSRF-Token', value = csrf)

        resp.status = falcon.HTTP_200
