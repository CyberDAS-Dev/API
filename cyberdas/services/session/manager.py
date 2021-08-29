from .session import Session

from datetime import datetime
import secrets

from cyberdas.exceptions import BadAuthError, NoSessionError


class SessionManager:

    '''
    Класс, управляющий пользовательскими сессиями. Позволяет централизовать весь
    код, связанный с сессиям и упростить введение правок.
    '''

    def __init__(self):
        self.session = Session

    def gen_token(cls, length = 32):
        '''
        Генерирует случайную 256-битную (по умолчанию) строку.

        Аргументы:
            length(int, опционально): число байт в токене
        '''
        return secrets.token_urlsafe(length)

    def start(self, db, **kwargs):
        '''
        Начинает новую сессию, возвращая словарь с параметрами куки и
        CSRF-токен.

        Аргументы:
            db(необходим): активная сессия БД

            kwargs(dict, необходимо): словарь со значениями всех полей в базе
                данных, используемых для инициаилизации, например {'uid': '2'}
        '''
        # Генерируем безопасные токены для идентификатора сессии и csrf-токена
        sid = self.gen_token()
        csrf_token = self.gen_token()

        # Добавляем новую сессию в базу данных
        self.session.new(db, sid = sid, csrf_token = csrf_token, **kwargs)
        return self.session.form_cookie(sid), csrf_token

    def refresh(self, db, **ids):
        '''
        Продлевает заданную сессию на еще один период действия сессии.
        Возвращает куки с новым временем истечения.

        Аргументы:
            db(необходим): активная сессия БД

            ids(неободимо): словарь из аргументов, использующихся для
                однозначной идентификации объекта в БД, например {'id': 2}
        '''
        self.session.prolong(db, **ids)
        return self.session.form_cookie(ids['sid'])

    def end(self, db, **ids):
        '''
        Заканчивает заданную сессию. Возвращает куки, которые позволяют
        закончить сессию на стороне клиентов.

        Аргументы:
            db(необходим): активная сессия БД

            ids(неободимо): словарь из аргументов, использующихся для
                однозначной идентификации объекта в БД, например {'id': 2}
        '''
        self.session.terminate(db, **ids)
        return self.session.form_cookie(ids['sid'], -1)

    def authenticate(self, db, cookie):
        '''
        Аутентифицирует пользователя по его куки. Возвращает словарь с
        информацией о сессии.

        Аргументы:
            db(необходим): активная сессия в базе данных

            cookie(dict, необходим): словарь с куки запроса
        '''
        sid = self.session.extract_cookie(cookie)

        try:
            assert sid is not None
            assert len(sid) == 43  # len(self.gen_token())
            assert sid.find('\x00') == -1
            ses = self.session.get(db, sid = sid)
            assert ses.expires.replace(tzinfo = None) > datetime.now()
        except (AssertionError, NoSessionError):
            raise BadAuthError

        return {'uid': ses.uid, 'sid': ses.sid, 'csrf_token': ses.csrf_token,
                'ip': ses.ip, 'agent': ses.user_agent}
