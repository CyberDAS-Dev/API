from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime
)
from sqlalchemy.orm import relationship

from .__meta__ import Base
from cyberdas.utils.hash_type import HashType


class LongSession(Base):
    '''
        Объект БД, хранящий информацию о выданных токенах, позволяющих
        аутентифицироваться без ввода пароля.

        Поля:
            id - Primary key Integer
                Идентификатор, используемый внутри базы данных.

            selector - Unique String
                Уникальная строка, передающаяся клиенту, и идентифицирующая
                конкретную серию токенов. Позволяет обнаруживать кражи токенов
                и защищает от атак по времени.

            validator - HashType
                Токен, передающийся клиенту. Хранится в хэшированном виде

            uid - Foreign key Integer
                Уникальный идентификатор пользователя, с которым связан токен

            user_agent - Text
                Хранит информацию о User Agent пользователя

            ip - Text
                Хранит информацию о IP пользователя

            expires - DateTime
                Хранит время истечения токена

        Взаимоотношения:
            user - многие-к-одному
                Задает соответствие между пользователем и его токенами
    '''

    __tablename__ = 'long_sessions'
    id = Column(Integer, primary_key = True)
    selector = Column(String(16), nullable = False, unique = True)
    validator = Column(HashType('sha256'), nullable = False)
    uid = Column(Integer, ForeignKey('users.id'), nullable = False)
    user_agent = Column(Text, nullable = False)
    ip = Column(String(16), nullable = False)
    expires = Column(DateTime(timezone = True), nullable = False)

    user = relationship('User', back_populates = 'long_session')
