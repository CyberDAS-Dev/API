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
from sqlalchemy_utils import EmailType, PasswordType, force_auto_coercion

from .__meta__ import Base

force_auto_coercion()

class User(Base):
    '''
        Объект БД, хранящий информацию о пользователе.

        Поля:
            id - Primary key Integer
                Уникальный идентификатор, используемый для внутренних ссылок

            email - Unique EmailType
                Хранит электронную почту пользователя, используется как логин для пользователя

            password - PasswordType
                Хранит пароль пользователя. Для хэширования используется PBKDF2
            
            name - Text
                Хранит имя пользователя

            surname - Text
                Хранит фамилию пользователя

            patronymic - Nullable Text
                Хранит отчество пользователя, необязательное поле

            faculty_id - Integer
                Хранит идентификатор факультета, на котором учится пользователя

            email_verified - Boolean
                'Галочка' верификации адреса электронной почты
        
            verified - Boolean
                'Галочка' полной верификации. Может быть поставлена только после email_verified

            created_at - DateTime
                Хранит дату регистрации пользователя
                При регистрации пользователя автоматически устанавливается БД с помощью SQL now()

            last_seen - DateTime 
                Хранит дату последней активности пользователя
                При регистрации пользователя автоматически устанавливается БД с помощью SQL now()

        Взаимоотношения:
            faculty - многие-к-одному
                Задает соответствие между пользователем и факультетом его обучения
    '''

    __tablename__ = 'users'
    id = Column(Integer, primary_key = True)
    email = Column(EmailType, nullable = False, unique = True)
    password = Column(PasswordType(schemes = ['pbkdf2_sha512']), nullable = False)
    name = Column(Text, nullable = False)
    surname = Column(Text, nullable = False)
    patronymic = Column(Text, nullable = True)
    faculty_id = Column(Integer, ForeignKey('faculties.id'), nullable = False)
    email_verified = Column(Boolean, nullable = False)
    verified = Column(Boolean, nullable = False)
    created_at = Column(DateTime(timezone = True), nullable = False,
                          server_default = func.now())
    last_seen = Column(DateTime(timezone = True), nullable = False,
                       server_default = func.now())

    faculty = relationship('Faculty', back_populates = 'population')