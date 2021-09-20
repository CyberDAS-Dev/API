import falcon
from itsdangerous import URLSafeTimedSerializer, BadData

from cyberdas.config import get_cfg
cfg = get_cfg()
serializer = URLSafeTimedSerializer(cfg['security']['secret.ott'])
max_age = int(cfg['internal']['ott.length'])


def generate_ott(data):
    return serializer.dumps(data)


def validate_ott(token):
    try:
        data = serializer.loads(token, max_age)
    except BadData:
        return False
    return data


def support_ott(req: falcon.Request, resp: falcon.Response, resource, params):
    '''
    Хук, который добавляет эндпоинту поддержку аутентификации по одноразовому
    токену.

    Модифицирует контекст, добавляя в него всё то, что было передано в токене.

    Требует авторизационного заголовка с токеном в запросе. Этот токен не
    является настоящим подтверждением идентичности, так как для его генерации
    достаточно знать адрес почты существующего пользователя. Не рекомендуется
    к использованию на критичных эндпоинтах.
    '''
    # Если пользователь уже аутентифицировался, ничего не делаем
    if req.context.user is not None:
        return

    # Извлекаем заголовок авторизации
    auth_header = req.get_header('Authorization')
    if auth_header is None:
        raise falcon.HTTPUnauthorized(
            description = 'В запросе отсутствует заголовок Authorization'
        )

    splitted = auth_header.split(' ')
    if len(splitted) != 2:
        raise falcon.HTTPUnauthorized(
            description = 'Некорректные данные в заголовке Authorization'
        )

    if splitted[0] != 'Bearer':
        raise falcon.HTTPUnauthorized(
            description = 'Неизвестный способ авторизации'
        )

    # Извлекаем данные из токена
    content = validate_ott(splitted[1])
    if content is False:
        raise falcon.HTTPUnauthorized(
            description = 'Недействительный токен в заголовке Authorization'
        )

    # То, что было в токене - передается в контекст запроса
    req.context.logger.info('[OTT][ИСПОЛЬЗОВАН] uid %s, resource %s'
                            % (content['uid'], req.uri))
    req.context['user'] = content
