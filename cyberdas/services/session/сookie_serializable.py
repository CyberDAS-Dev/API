class CookieSerializable:

    '''
    Класс, предоставляющий методы упаковываний сессий для передачи клиентам
    в виде куки.

    Для его использования нужно в наследнике определить 'cookie_name' - имя
    куки, соответствующее этому типу сессий.
    '''

    cookie_name = None

    @classmethod
    def safe_cookie(cls, cookie_params):
        '''
        Добавляет в словарь параметры для формирования куки, повышающие
        безопасность их использования.
        А именно:
        * `secure` - позволяет использовать куки только при HTTPS соединении
        * `http_only` - не позволяет манипулировать куки с помощью JS
        * `same_site` - не позволяет отправлять куки на другие домены

        Аргументы:
            cookie_params(dict, необходим): словарь с параметрами, используемыми
                для формирования куки
        '''
        safe_params = {'secure': True, 'http_only': True,
                       'same_site': 'Strict', 'path': '/'}
        cookie_params.update(safe_params)
        return cookie_params

    @classmethod
    def form_cookie(cls, value, max_age = None):
        '''
        Возвращает словарь для формирования безопасного сессионного куки.

        Аргументы:
            value(string, необходим): значение, которое нужно хранить в куки

            max_age(int, опционально): максимальное время действия куки в
                секундах, в случае отсутствия используется length из определения
                класса
        '''
        return cls.safe_cookie({'name': cls.cookie_name, 'value': value,
                                'max_age': max_age or cls.length})

    @classmethod
    def extract_cookie(cls, cookies):
        '''
        Извлекает значение сессионного куки из словаря
        'имя'-'значение' с куки. Возвращает None в случае отсутствия.

        Аргументы:
            cookies(dict, необходим): словарь 'имя'-'значение' с куки
        '''
        try:
            return cookies[cls.cookie_name]
        except KeyError:
            return None
