import hashlib

from sqlalchemy import types
from sqlalchemy.dialects import oracle, postgresql, sqlite
from sqlalchemy.ext.mutable import Mutable


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


    Также, автоматически переводит хранимые хэши на новые алгоритмы
    хэширования, в случае устаревания старых.
    ::
        class Session(Base):
            sid = Column(HashType('sha512', deprecated = ['sha256']))

        Все хранимые в базе хэши, использующие `sha256`, будут перехэшированы
        `sha512` при первом получении оригинального значения (нехэшированного)
    '''

    impl = types.VARBINARY(512)
    cache_ok = True

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
        self.deprecated = set(deprecated)
        for algo in (self.algorithm, *self.deprecated):
            if algo not in hashlib.algorithms_available:
                raise Exception(f"{algo} недоступен")
        self._length = max_length

    @property
    def length(self):
        if self._length is None:
            lengths = []
            for algorithm in (self.algorithm, *self.deprecated):
                lengths.append(hashlib.new(algorithm).digest_size)
            self._length = max(lengths)

        return self._length

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
        ему метод проверки значений.
        '''
        if value is not None:
            return Hash(value, self.check)

    def hash_with(self, data, algorithm):
        '''
        Метод хэширования, превращающий входные данные в байтовый дайджест,
        используя данный алгоритм.
        '''
        if isinstance(data, str):
            data = data.encode()
        hashing = hashlib.new(algorithm)
        hashing.update(data)
        return hashing.digest()

    def _hash(self, data):
        '''
        Метод хэширования, использующий указанный пользователем алгоритм
        '''
        return self.hash_with(data, self.algorithm)

    def check(self, data, hash):
        '''
        Метод, проверяющий не является ли hash хэш суммой от data, используя все
        указанные пользователем алгоритмы. В случае, если hash был сгенерирован
        алгоритмом, теперь считающимся устаревшим, возвращает также новую
        хэш-сумму от data, использующую новый алгоритм.

        Результат проверки возвращается в `equal`, новая хэш-сумма - в `new`.
        '''
        equal, new, this_algo = False, '', ''
        for algorithm in (self.algorithm, *self.deprecated):
            if (hash == self.hash_with(data, algorithm)):
                equal = True
                this_algo = algorithm
                break
        if equal and (this_algo in self.deprecated):
            new = self._hash(data)
        return equal, new

    def coercion_listener(self, target, value, oldvalue, initiator):
        '''
        Перехватывает входящие вызовы `coerce`, направленные к Hash и лично
        приводит входящие данные к типу Hash. Это необходимо из-за того, что
        Hash требует метод `check` в конструкторе, и этот метод находится в
        этом (HashType) классе.
        '''
        if value is None:
            return

        if not isinstance(value, Hash):
            value = self._hash(value)
            return Hash(value, self.check)

        return value


class Hash(Mutable, object):
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

    @classmethod
    def coerce(cls, key, value):
        '''
        Приводит входящие данные к данному типу. Имеет такой вид, так как
        это приведение перенесено в HashType.
        '''
        if isinstance(value, Hash):
            return value

    def __init__(self, hash: bytes, check: callable):
        self.hash = hash
        self.check = check

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
            equal, new = self.check(value, self.hash)
            if equal and new:  # если хэш-алгоритм оказался устаревшим
                self.hash = new
                self.changed()
            return equal

        return False

    def __ne__(self, value):
        return not (self == value)

    def __hash__(self) -> int:
        return super().__hash__()


Hash.associate_with(HashType)  # Позволяет перехватывать вызовы `coerce`
