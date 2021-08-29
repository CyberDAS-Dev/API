from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Text,
    DateTime,
    Boolean
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy_utils import EmailType

from .__meta__ import Base


class User(Base):
    '''
        Объект БД, хранящий информацию о пользователе.

        Поля:
            id - Primary key Integer
                Уникальный идентификатор, используемый для внутренних ссылок

            email - Unique EmailType
                Хранит электронную почту пользователя, используется как логин
                для пользователя

            name - Text
                Хранит имя пользователя

            surname - Text
                Хранит фамилию пользователя

            patronymic - Nullable Text
                Хранит отчество пользователя, необязательное поле

            faculty_id - Integer
                Хранит идентификатор факультета, на котором учится пользователя

            created_at - DateTime
                Хранит дату регистрации пользователя
                При регистрации пользователя автоматически устанавливается БД
                с помощью SQL now()

        Взаимоотношения:
            faculty - многие-к-одному
                Задает соответствие между пользователем и факультетом его
                обучения

            sessions - один-ко-многим
                Задает соответствие между пользователем и всеми его активными
                сессиями

            slots - один-ко-многим
                Задает соответствие между пользователем и его слотами
    '''

    __tablename__ = 'users'
    id = Column(Integer, primary_key = True)
    email = Column(EmailType, nullable = False, unique = True)
    name = Column(Text, nullable = False)
    surname = Column(Text, nullable = False)
    patronymic = Column(Text, nullable = True)
    faculty_id = Column(Integer, ForeignKey('faculties.id'), nullable = False)
    created_at = Column(DateTime(timezone = True), nullable = False,
                        server_default = func.now())

    faculty = relationship('Faculty', back_populates = 'population')
    sessions = relationship('Session', back_populates = 'user')
    slots = relationship('Slot', back_populates = 'holder')
