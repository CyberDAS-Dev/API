from datetime import datetime, timedelta

from cyberdas.exceptions import NoSessionError


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
        Возвращает дату-время истечения сессии.

        Аргументы:
            db(необходимо): активная сессия БД

            kwargs(неободимо): словарь из аргументов, использующихся в
                инициализации объекта, например при {'id': 2, 'name': 'Иван'}
                объект будет инициализирован с полями `id = 2` и `name = 'Иван'`
        '''
        expires = datetime.now() + timedelta(seconds = cls.length)
        new_object = cls.classname(
            expires = expires,
            **kwargs
        )
        db.add(new_object)
        return expires

    @classmethod
    def prolong(cls, db, **ids):
        '''
        Продлевает время жизни объекта на еще одну полную длительность действия
        этого типа сессий.
        Возвращает дату-время нового истечения сессии.

        Аргументы:
            db(необходимо): активная сессия БД

            ids(неободимо): словарь из аргументов, использующихся для
                однозначной идентификации объекта в БД, например {'id': 2}
        '''
        session = cls.find(db, **ids)
        if session.first() is None:
            raise NoSessionError
        expires = datetime.now() + timedelta(seconds = cls.length)
        session.update({cls.classname.expires: expires})
        return expires

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
