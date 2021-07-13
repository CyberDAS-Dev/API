from datetime import datetime, timedelta
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
from ..config import get_cfg

session_length = int(get_cfg()['internal']['session.length'])


class Session(Base):
    '''
        Объект БД, хранящий информацию о текущих сессиях.

        Поля:
            sid - Primary key String
                Уникальный идентификатор сессии, передающийся клиенту

            uid - Foreign key Integer
                Уникальный идентификатор пользователя, с которым связана сессия

            user_agent - Text
                Хранит информацию о User Agent пользователя

            ip - Text
                Хранит информацию о IP пользователя

            expires - DateTime
                Хранит время истечения сессии
                Sets on the DB server for first time to SQL now().

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
    user_agent = Column(Text, nullable = False)
    ip = Column(String, nullable = False)
    expires = Column(
        DateTime(timezone = True), nullable = False,
        default = datetime.now() + timedelta(seconds = session_length)
    )
    created_at = Column(
        DateTime(timezone = True), nullable = False,
        server_default = func.now()
    )

    user = relationship('User', back_populates = 'session')
