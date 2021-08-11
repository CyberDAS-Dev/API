from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    String,
    ForeignKey
)

from sqlalchemy.orm import relationship
from .__meta__ import Base
from cyberdas.utils.serializable_table import Serializable


class Slot(Base, Serializable):
    '''
        Объект БД, хранящий информацию о слоте в очереди.

        Поля:
            queue_name - Primary key Foreign key String
                Имя очереди, в которой находится этот слот

            id - Primary key Integer
                Уникальный идентификатор слота

            time - DateTime
                Время начала действия слота

            user_id - Nullable Foreign key Integer
                Идентификатор пользователя, занявшего слот
                Если равен Null - слот свободен

        Взаимоотношения:
            holder - один-ко-многим
                Задает соответствие между слотом и его держателем

            queue - один-ко-многим
                Указывает на очередь, в которой этот слот находится
    '''

    __tablename__ = 'slots'
    queue_name = Column(String, ForeignKey('queues.name'), primary_key = True)
    id = Column(Integer, primary_key = True)
    time = Column(DateTime, nullable = False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable = True)

    holder = relationship('User', back_populates = 'slots')
    queue = relationship('Queue', back_populates = 'slots')
