import hashlib

from sqlalchemy import types
from sqlalchemy.dialects import oracle, postgresql, sqlite


class HashType(types.TypeDecorator):
    '''
    Тип данных SQLAlchemy, позволяющий хранить значения в базе данных в виде
    хэш-сумм, и не заботится о сравнении с этим хэшем других значений.

    ::
        class Session(Base):
            sid = Column(HashType('sha256'))

        session = Session()
        session.sid = '123'

        print(session.sid)
        # 'a665a4592042...'

        session.sid == '123'
        # True
    '''

    impl = types.VARBINARY(512)

    def __init__(self, algorithm, deprecated = [], max_length = None):
        '''
        Аргументы:

            algorithms(str, необходим): алгоритм, используемый для генерации
                хэш-сумм

            deprecated(list, опционально): список устаревших алгоритмов, которые
                раньше использовались для формирования хэш-сумм

            max_length(int, опционально): максимальная длина поля
        '''
        self.algorithm = algorithm
        if algorithm not in hashlib.algorithms_available:
            raise Exception(f"{algorithm} недоступен, выберите другой")
        self.length = hashlib.new(algorithm).digest_size

    def load_dialect_impl(self, dialect):  # pragma: no cover
        if dialect.name == 'postgresql':
            impl = postgresql.BYTEA(self.length)
        elif dialect.name == 'oracle':
            impl = oracle.RAW(self.length)
        elif dialect.name == 'sqlite':
            impl = sqlite.BLOB(self.length)
        else:
            impl = types.VARBINARY(self.length)
        return dialect.type_descriptor(impl)

    def process_bind_param(self, value, dialect):
        '''
        Вызывается при передаче значения на хранение в базу данных.

        Оставляет объекты класса Hash нетронутыми, остальное хэширует.
        '''
        if isinstance(value, Hash):
            return value.hash

        if isinstance(value, (str, bytes)):
            return self._hash(value)

    def process_result_value(self, value, dialect):
        '''
        Вызывается при получении значений из базы данных.

        Превращает байтовые строки в объект класса Hash, попутно передавая
        ему метод хэширования.
        '''
        if value is not None:
            return Hash(value, self._hash)

    def _hash(self, data):
        '''
        Метод хэширования, переводящий входные данные в байтовый дайджест,
        используя указанный пользователем алгоритм.
        '''
        if isinstance(data, str):
            data = data.encode()
        hashing = hashlib.new(self.algorithm)
        hashing.update(data)
        return hashing.digest()


class Hash(object):
    '''
    Класс, являющийся контейнером для хэш-сумм из базы данных.
    Позволяет легко сравнивать хранимую хэш-сумму со строками на предмет того,
    является ли хэш-сумма сравниваемой строки - нашей хранимой хэш-суммой.

    На практике это позволяет выдавать клиенту строку/значение, например,
    идентификатор сессии, но в БД хранить только его хэш (из сображений
    безопасности) и при этом легко находить эту сессию при поступлении от
    клиента оригинального значения.

    Важно: самостоятельное использование этого класса (в отрыве от SQLAlchemy)
    возможно только при гарантии того, что `hash` переданный в конструктор
    действительно будет хэш-суммой какой-то строки/значения.
    В SQLAlchemy это гарантируется HashType::process_bind_param, конкретно -
    тем, что все приходящие в БД значения, которые будут храниться в колонках
    типа HashType превращаются в свою хэш-сумму.
    '''

    def __init__(self, hash: bytes, hashing):
        self.hash = hash
        self.hashing = hashing

    def __str__(self):
        return self.hash.hex()

    def encode(self, *args, **kwargs):
        return self.hash.hex().encode(*args, **kwargs)

    def __eq__(self, value):
        if self.hash is None or value is None:
            return self.hash is value

        if isinstance(value, Hash):
            return value.hash == self.hash

        if isinstance(value, (str, bytes)):
            return self.hash == self.hashing(value)

        return False

    def __ne__(self, value):
        return not (self == value)

    def __hash__(self) -> int:
        return super().__hash__()
