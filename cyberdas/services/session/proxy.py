from .manager import SessionManager

from cyberdas.exceptions import BadAuthError


class ManagerProxy:

    '''
    Класс, проксирующий запросы к SessionManager. Он нужен для упрощения вида
    вызовов методов, так как он занимается преобразование аргументов и ведением
    логов.

    Во внешние модули экспортируется как SessionManager.
    '''

    def __init__(self):
        self.manager = SessionManager()

    def start_session(self, req, user):
        kwargs = {'ip': req.access_route[-1], 'uid': user.id,
                  'user_agent': req.user_agent}
        db = req.context.session
        result = self.manager.start_session(db, **kwargs)

        req.context.logger.info('[НОВАЯ СЕССИЯ] uid %s' % user.id)
        return result

    def start_l_session(self, req, user, assoc_cookie):
        kwargs = {'ip': req.access_route[-1], 'uid': user.id,
                  'user_agent': req.user_agent,
                  'associated_sid': assoc_cookie['value']}
        db = req.context.session
        result = self.manager.start_l_session(db, **kwargs)

        req.context.logger.info('[НОВАЯ ДОЛГАЯ СЕССИЯ] uid %s' % user.id)
        return result

    def continue_session(self, req):
        db = req.context.session
        result, uid = self.manager.continue_session(db, req.cookies)

        req.context.logger.info('[ВХОД ПО ТОКЕНУ] uid %s' % uid)
        return result

    def end_session(self, req):
        db = req.context.session
        user = req.context.user

        ids = {'sid': user['sid']}
        result = self.manager.end_session(db, **ids)

        req.context.logger.debug("[КОНЕЦ СЕССИИ] uid %s" % user['uid']) # noqa
        return result

    def refresh_session(self, req):
        db = req.context.session
        user = req.context.user

        ids = {'sid': user['sid']}
        result = self.manager.refresh_session(db, **ids)

        req.context.logger.debug("[ПРОДЛЕНА СЕССИЯ] uid %s" % user['uid'])
        return result

    def authorize(self, req):
        db = req.context.session
        cookie = req.cookies

        try:
            result = self.manager.authorize(db, cookie)
            return result
        except BadAuthError:
            req.context.logger.warning("[ПОДДЕЛЬНАЯ СЕССИЯ]")
            raise