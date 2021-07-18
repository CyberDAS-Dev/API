from datetime import datetime, timedelta

import cyberdas.models.session
import cyberdas.models.long_session
from cyberdas.config import get_cfg
from cyberdas.exceptions import NoSessionError, SecurityError

cfg = get_cfg()


class AbstractSession:

    '''
    Абстрактный класс без экземпляров, являющийся интерфейсом к объекту
    сессии в БД.

    Для полной реализации нужно определить в наследнике `classname` - класс
    этого типа сессий из базы данных, `length` - длительность этого типа сессий
    и метод `filter`, который должен оставлять из входящих аргументов только те,
    по которым идентифицируются объекты этого типа сессий.
    '''

    classname = None
    length = 0

    @classmethod
    def filter(cls, **ids):
        '''
        Фильтрует передаваемые словарные аргументы до необходимого минимума,
        используемого для идентификации объекта. Также, проверяет их наличие.

        Аргументы:
            ids(неободимо): словарь из аргументов, использующихся для
                идентификации объекта в БД, например {'id': 2}
        '''
        raise NotImplementedError

    @classmethod
    def find(cls, db, **ids):
        '''
        Возвращает выражение для поиска объекта в БД. Такое возвращемое значение
        нужно для операций обновления.

        Аргументы:
            db(необходимо): активная сессия БД

            ids(неободимо): словарь из аргументов, использующихся для
                однозначной идентификации объекта в БД, например {'id': 2}
        '''
        session = db.query(cls.classname).filter_by(**cls.filter(**ids))
        return session

    @classmethod
    def get(cls, db, **ids):
        '''
        Возвращает объект из БД. В случае отсутствия такого объекта, возвращает
        ошибку `NoSessionError`.

        Аргументы:
            db(необходимо): активная сессия БД

            ids(неободимо): словарь из аргументов, использующихся для
                однозначной идентификации объекта в БД, например {'id': 2}
        '''
        ses = cls.find(db, **ids).first()
        if (ses is not None):
            return ses
        else:
            raise NoSessionError

    @classmethod
    def new(cls, db, **kwargs):
        '''
        Создает новый объект сессий, автоматически устанавливая время действия
        и передавая любые параметры, использующиеся при инициализации объекта.

        Аргументы:
            db(необходимо): активная сессия БД

            kwargs(неободимо): словарь из аргументов, использующихся в
                инициализации объекта, например при {'id': 2, 'name': 'Иван'}
                объект будет инициализирован с полями `id = 2` и `name = 'Иван'`
        '''
        new_object = cls.classname(
            expires = datetime.now() + timedelta(seconds = cls.length),
            **kwargs
        )
        db.add(new_object)

    @classmethod
    def prolong(cls, db, **ids):
        '''
        Продлевает время жизни объекта на еще одну полную длительность действия
        этого типа сессий.

        Аргументы:
            db(необходимо): активная сессия БД

            ids(неободимо): словарь из аргументов, использующихся для
                однозначной идентификации объекта в БД, например {'id': 2}
        '''
        session = cls.find(db, **ids)
        if session is None:
            raise NoSessionError
        session.update({cls.classname.expires: datetime.now() + timedelta(seconds = cls.length)}) # noqa
        return cls.length

    @classmethod
    def terminate(cls, db, **ids):
        '''
        Уничтожает объект в БД.

        Аргументы:
            db(необходимо): активная сессия БД

            ids(неободимо): словарь из аргументов, использующихся для
                однозначной идентификации объекта в БД, например {'id': 2}
        '''
        session = cls.get(db, **ids)
        db.delete(session)


class Session(AbstractSession):

    classname = cyberdas.models.session.Session
    length = int(cfg['internal']['session.length'])

    @classmethod
    def filter(cls, **ids):
        return {'sid': ids['sid']}


class LongSession(AbstractSession):

    classname = cyberdas.models.long_session.LongSession
    length = int(cfg['internal']['remember.length']) * 3600

    @classmethod
    def filter(cls, **ids):
        if 'validator' in ids:
            return {'selector': ids['selector'], 'validator': ids['validator']}
        else:
            return {'selector': ids['selector']}

    @classmethod
    def get(cls, db, **ids):
        try:
            ses = super().get(db, **ids)
        except NoSessionError:
            validator = ids.pop('validator')
            series = cls.find(db, **ids).first()
            if series is not None:
                raise SecurityError(f'[УКРАДЕННЫЙ ТОКЕН] {ids["selector"]}:{validator}') # noqa

        return ses

    @classmethod
    def change(cls, db, new_validator, new_association, **ids):
        # TODO: некрасивый метод, переписать
        old = cls.find(db, **ids)
        old.update({cls.classname.validator: new_validator,
                    cls.classname.associated_sid: new_association})
