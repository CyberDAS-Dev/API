from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .__meta__ import Base


class Session(Base):
    '''
        Объект БД, хранящий информацию о текущих сессиях.

        Поля:
            sid - Primary key String
                Уникальный идентификатор сессии, передающийся клиенту

            uid - Foreign key Integer
                Уникальный идентификатор пользователя, с которым связана сессия

            csrf_token - Unique String
                Уникальная строка, присвоенная пользователю для защиты от
                CSRF атак

            user_agent - Text
                Хранит информацию о User Agent пользователя

            ip - Text
                Хранит информацию о IP пользователя

            expires - DateTime
                Хранит время истечения сессии

            created_at - DateTime
                Хранит дату последней выдачи куки
                При выдаче куки автоматически устанавливается БД с помощью
                SQL now()

        Взаимоотношения:
            user - многие-к-одному
                Задает соответствие между пользователем и всеми его сессиями
    '''

    __tablename__ = 'sessions'
    sid = Column(String, primary_key = True)
    uid = Column(Integer, ForeignKey('users.id'), nullable = False)
    csrf_token = Column(String, unique = True, nullable = False)
    user_agent = Column(Text, nullable = False)
    ip = Column(String, nullable = False)
    expires = Column(DateTime(timezone = True), nullable = False)
    created_at = Column(
        DateTime(timezone = True), nullable = False,
        server_default = func.now()
    )

    user = relationship('User', back_populates = 'session')
