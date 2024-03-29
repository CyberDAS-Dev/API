from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Text,
    DateTime,
    Boolean,
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

            faculty_id - Nullable Integer
                Хранит идентификатор факультета, на котором учится пользователя

            course - Nullable Integer
                Хранит текущий курс обучения пользователя

            building - Nullable Integer
                Хранит корпус проживания пользователя

            room - Nullable Integer
                Хранит комнату проживания пользователя

            quick - Boolean
                Флаг, сигнализирующий о том, что пользователь не проходил полной
                процедуры регистрации, а был зарегистрирован с помощью
                `quick_auth`

            created_at - DateTime
                Хранит дату регистрации пользователя
                При регистрации пользователя автоматически устанавливается БД
                с помощью SQL now()

            last_session - DateTime
                Хранит дату начала последней сессии пользователя
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
    faculty_id = Column(Integer, ForeignKey('faculties.id'), nullable = True)
    course = Column(Integer, nullable = True)
    building = Column(Integer, nullable = True)
    room = Column(Integer, nullable = True)
    quick = Column(Boolean, nullable = False, server_default = 'false')
    created_at = Column(DateTime, nullable = False, server_default = func.now())
    last_session = Column(DateTime, nullable = False,
                          server_default = func.now())

    faculty = relationship('Faculty', back_populates = 'population')
    sessions = relationship('Session', back_populates = 'user')
    slots = relationship('Slot', back_populates = 'holder')
    maintenances = relationship('Maintenance', back_populates = 'user')
