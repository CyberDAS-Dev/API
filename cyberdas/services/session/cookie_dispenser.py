from .db_interface import Session, LongSession


class CookieDispenser:

    '''
    Класс без экземпляров, предоставляющий методы упаковываний сессий для
    передачи клиентам в виде куки.
    '''

    ses_len = Session.length
    remember_len = LongSession.length

    @classmethod
    def safe_cookie(cls, cookie_params):
        '''
        Добавляет параметры куки, повышающие безопастность их использования.
        А именно:
        * `secure` - позволяет использовать куки только при HTTPS соединении
        * `http_only` - не позволяет манипулировать куки с помощью JS
        * `same_site` - не позволяет отправлять куки на другие домены

        Аргументы:
            cookie_params(dict, необходим): словарь с параметрами, используемыми
                для формирования куки
        '''
        safe_params = {'secure': True, 'http_only': True, 'same_site': 'Strict'}
        cookie_params.update(safe_params)
        return cookie_params

    @classmethod
    def session_cookie(cls, sid, max_age = None):
        '''
        Формирует безопасный сессионный куки.

        Аргументы:
            sid(string, необходим): значение sid сессии из БД

            max_age(int, опционально): максимальное время действия куки в
                секундах, в случае отсутствия используется указанное в конфиге
        '''
        return cls.safe_cookie({'name': 'SESSIONID', 'value': sid,
                                'max_age': max_age or cls.ses_len})

    @classmethod
    def extract_session(cls, cookies):
        '''
        Извлекает сессионный куки из их множества. Возвращает None в случае
        отсутствия.

        Аргументы:
            cookies(dict, необходим): словарь с куки
        '''
        try:
            return cookies['SESSIONID']
        except KeyError:
            return None

    @classmethod
    def l_session_cookie(cls, selector, validator, max_age = None):
        '''
        Формирует безопасный куки для долгой сессии.

        Аргументы:
            selector(string, необходим): значение selector сессии из БД

            validator(string, необходим): значение validator сессии из БД

            max_age(int, опционально): максимальное время действия куки в
                секундах, в случае отсутствия используется указанное в конфиге
        '''
        return cls.safe_cookie({'name': 'REMEMBER',
                                'value': f'{selector}:{validator}',
                                'max_age': max_age or cls.remember_len})

    @classmethod
    def extract_l_session(cls, cookies):
        '''
        Извлекает селектор и валидатор долгой сессии из множества куки.
        Возвращает None в случае их отсутствия.

        Аргументы:
            cookies(dict, необходим): словарь с куки
        '''
        try:
            return cookies['REMEMBER'].split(':')
        except KeyError:
            return None
