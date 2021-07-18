from datetime import datetime
import secrets

from cyberdas.exceptions import BadAuthError, NoSessionError, SessionError

from .db_interface import Session, LongSession
from .cookie_dispenser import CookieDispenser


class SessionManager:

    '''
    Класс, управляющий пользовательскими сессиями. Позволяет централизовать весь
    код, связанный с сессиям и упростить введение правок.

    Не экспортируется во внешние модули, для этого используется ManagerProxy,
    значительно упрощающий вызов методов.
    '''

    def __init__(self):
        self.session = Session
        self.l_session = LongSession
        self.cookie = CookieDispenser

    def gen_token(cls, length = 32):
        '''
        Генерирует случайную 256-битную (по умолчанию) строку.

        Аргументы:
            length(int, опционально): число байт в токене
        '''
        return secrets.token_urlsafe(length)

    def start_session(self, db, continued = False, **kwargs):
        '''
        Начинает новую обычную сессию, возвращая словарь с параметрами куки и
        csrf-токен.

        Аргументы:
            db(необходим): активная сессия БД

            continued(boolean, опционально): была ли сессия начата без ввода
                пароля

            kwargs(dict, необходимо): словарь со значениями всех полей в базе д
                анных, используемых для инициаилизации, например {'uid': '2'}
        '''
        # Генерируем безопасные токены для идентификатора сессии и csrf-токена
        sid = self.gen_token()
        csrf_token = self.gen_token()

        # Добавляем новую сессию в базу данных
        self.session.new(
            db, sid = sid, csrf_token = csrf_token, unsafe = continued, **kwargs
        )
        return self.cookie.session_cookie(sid), csrf_token

    def start_l_session(self, db, series = '', **kwargs):
        '''
        Начинает новую долгую сессию, возвращая словарь с параметрами куки.

        Аргументы:
            db(необходим): активная сессия БД

            series(string, опционально): если предоставлено значение, то новая
                сессия будет принадлежать к заданной линейке токенов, иначе
                будет создана новая

            kwargs(dict, необходимо): словарь со значениями всех полей в базе д
                анных, используемых для инициаилизации, например {'uid': '2'}
        '''
        # Генерируем безопасные токены для идентификатора сессии и csrf-токена
        selector = series or self.gen_token(12)
        validator = self.gen_token()

        # Добавляем новую сессию в базу данных
        self.l_session.new(
            db, selector = selector, validator = validator, **kwargs
        )
        return self.cookie.l_session_cookie(selector, validator)

    def continue_session(self, db, cookies):
        '''
        Начинает новую короткую сессию и создает новую долгую сессию, если
        у пользователя есть на это право. Возвращает словари с параметрами куки,
        соответствующие двум сессиям и csrf-токен.
        В случае, если пользователь не может воспользоваться токеном, возвращает
        ошибку

        Аргументы:
            db(необходим): активная сессия БД

            cookies(dict, необходимо): предоставленные пользователям куки
        '''
        # Извлекаем селектор и валидатор из куки
        selector, validator = self.cookie.extract_l_session(cookies)
        ids = {'selector': selector, 'validator': validator}

        # TODO: различать несовпадене селектора от несовпадения валидатора

        old = self.l_session.get(db, **ids)

        # Проверяем, что токен не просрочен
        if old.expires.replace(tzinfo = None) < datetime.now():
            raise SessionError("Токен просрочен")

        # Проверяем, что ассоциированная сессия завершена
        try:
            associated_ses = self.session.get(db, sid = old.associated_sid)
            if associated_ses is not None:
                raise SessionError("Ассоциированная сессия еще на завершена")
        except NoSessionError:
            pass

        # Продлеваем токен на еще один период длительности
        self.l_session.prolong(db, **ids)

        # Создаем новую короткую сессию и извлекаем новую ассоциацию
        s_cookie, csrf_token = self.start_session(
            db, continued = True,
            uid = old.uid, user_agent = old.user_agent, ip = old.ip
        )
        new_association = s_cookie['value']  # TODO: надо абстрагировать (?)

        # Меняем валидатор и ассоциацию на новые и пакуем новый токен в куки
        new_validator = self.gen_token()
        self.l_session.change(db, new_validator, new_association, **ids)
        l_cookie = self.cookie.l_session_cookie(selector, new_validator)

        return (l_cookie, s_cookie, csrf_token), old.uid

    def end_session(self, db, **ids):
        '''
        Заканчивает заданную короткую сессию, а так же, если она есть, закрывает
        долгую сессию, связанную с этой короткой. Возвращает массив с
        параметрами куки, которые позволяют удалить их на стороне клиентов.

        Аргументы:
            db(необходим): активная сессия БД

            ids(неободимо): словарь из аргументов, использующихся для
                однозначной идентификации объекта в БД, например {'id': 2}
        '''
        to_return = list()
        ses = self.session.get(db, **ids)

        # Ищем ассоциированные сессии, прерываем их и формируем куки
        if len(ses.associated) == 1:
            selector, validator = ses.associated[0].selector, ses.associated[0].validator # noqa
            self.l_session.terminate(db, selector = selector, validator = validator) # noqa
            to_return.append(self.cookie.l_session_cookie(selector, validator, -1)) # noqa

        # Прерываем сессию и формируем новые куки
        self.session.terminate(db, **ids)
        to_return.append(self.cookie.session_cookie(ids['sid'], -1))
        return to_return

    def refresh_session(self, db, **ids):
        '''
        Продлевает заданную сессию на еще один период действия сессии.
        Возвращает куки с новым временем истечения.

        Аргументы:
            db(необходим): активная сессия БД

            ids(неободимо): словарь из аргументов, использующихся для
                однозначной идентификации объекта в БД, например {'id': 2}
        '''
        self.session.prolong(db, **ids)
        return self.cookie.session_cookie(ids['sid'])

    def authorize(self, db, cookie):
        '''
        Аутентифицирует пользователя по его куки. Возвращает словарь с
        информацией о сессии.

        Аргументы:
            db(необходим): активная сессия в базе данных

            cookie(dict, необходим): словарь с куки запроса
        '''
        sid = self.cookie.extract_session(cookie)
        ids = {'sid': sid}

        try:
            assert sid is not None
            assert len(sid) == 43  # len(self.gen_token())
            assert sid.find('\x00') == -1
            ses = self.session.get(db, **ids)
            assert ses.expires.replace(tzinfo = None) > datetime.now()
        except (AssertionError, NoSessionError):
            raise BadAuthError

        return {'uid': ses.uid, 'sid': ses.sid, 'csrf_token': ses.csrf_token}
