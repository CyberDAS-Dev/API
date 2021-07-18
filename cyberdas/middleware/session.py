import falcon

from cyberdas.services.session import SessionManager


class SessionMiddleware:

    def __init__(self, api, exempt_routes = list(), exempt_methods = list()):
        '''
        Класс, содержащий сессионный middleware. Для настройки исключений
        используется проход по всем эндпоинтам и поиск настроек в аттрибутах
        классов, также можно передать эти параметры в аргументах конструктора.

        Аргументы:
            api(falcon.App, необходим): ссылка на экземпляр API.

            exempt_routes(list, опционально): список путей, не требущих
            аутентификации.

            exempt_methods(list, опционально): список методов, не требующих
            аутентификации.
        '''
        self.manager = SessionManager()
        self.config = dict()
        self.config['exempt_routes'] = exempt_routes
        self.config['exempt_methods'] = dict()
        self.config['exempt_methods']['global'] = exempt_methods

        routes = self._get_all_routes(api)
        for route in routes:
            self._get_settings(*route)

    def _get_all_routes(self, api):
        '''
        Ищет все пары вида (класс ресурса, шаблон URI) в API

        Аргументы:
            api(falcon.App, необходим): ссылка на экземпляр API.
        '''
        routes = []

        def get_node_and_children(node):
            routes.append((node.resource, node.uri_template))
            if len(node.children):
                for child_node in node.children:
                    get_node_and_children(child_node)

        for node in api._router._roots:
            get_node_and_children(node)
        return routes

    def _get_settings(self, resource, uri_template):
        '''
        Собирает настройки из класса эндпоинта и добавляет их в глобальный
        конфиг.

        Аргументы:
            resource(необходим): ссылка на экземпляр класса эндпоинта.

            uri_template(string, необходим): строка, по которой производится
            маршрутизация к этому эндпоинту.
        '''
        local_conf = getattr(resource, 'auth', {})
        if local_conf.get('disabled'):
            self.config['exempt_routes'].append(uri_template)
        self.config['exempt_methods'][str(resource)] = local_conf.get('exempt_methods', []) # noqa

    def csrf_protect(self, req):
        '''
        Проверяет CSRF-токен всех POST-запросов. Выбрасывает исключение, если
        запрос не проходит проверку.

        Аргументы:
            req(необходим): текущий запрос.
        '''
        if req.method == 'POST':
            csrf = req.get_header('XCSRF-Token')
            if csrf is None or csrf != req.context['user']['csrf_token']:
                req.context.logger.error(
                    '[ПОПЫТКА CSRF] uid %s, sid %s'
                    % (req.context['user']['uid'], req.context['user']['sid'])
                )
                raise falcon.HTTPUnauthorized(
                    description = 'Неверный CSRF-токен'
                )

    def process_resource(self, req, resp, resource, params):
        '''
        Автоматически вызывается Falcon при получении запроса.

        Аутентифицирует пользователя, проверяет CSRF-токен, а также добавляет в
        контекст запроса информацию о пользователе и его сессии.
        '''
        exempted = (
            req.method in self.config['exempt_methods']['global']
            or req.uri_template in self.config['exempt_routes']
            or req.method in self.config['exempt_methods'][str(resource)]
        )

        if exempted:
            req.context['user'] = None
            return

        try:
            req.context['user'] = self.manager.authorize(req)
        except Exception:
            req.context['user'] = None
            raise falcon.HTTPUnauthorized

        self.csrf_protect(req)
