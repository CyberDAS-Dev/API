from sqlalchemy import (
    Column,
    Integer,
    Text
)
from sqlalchemy.orm import relationship

from .__meta__ import Base

class Faculty(Base):
    '''
        Объект БД, хранящий информацию о факультете.

        Поля:
            id - Primary key Integer
                Уникальный идентификатор, используемый для внутренних ссылок

            name - Unique Text
                Хранит название факультета (в формате: 'Геологический')
                Смотрите static.faculties для информации

        Взаимоотношения:
            population - один-ко-многим
                Задает соответствие между факультетом и пользователями, которые на нем учатся
    '''

    __tablename__ = 'faculties'
    id = Column(Integer, primary_key = True)
    name = Column(Text, nullable = False, unique = True)

    population = relationship('User', back_populates = 'faculty')
