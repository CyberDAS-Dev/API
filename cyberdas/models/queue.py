from sqlalchemy import (
    Column,
    Text,
    String,
    Integer,
    Boolean
)

from sqlalchemy.orm import relationship
from .__meta__ import Base
from cyberdas.utils.serializable_table import Serializable


class Queue(Base, Serializable):
    '''
        Объект БД, хранящий информацию о очереди.

        Поля:
            name - Primary key String
                Уникальный идентификатор, используемый для внутренних ссылок

            title - Text
                Человекочитаемое содержательное название очереди

            description - Text
                Описание очереди

            duration - Integer
                Длительность действия слотов очереди

            waterfall - Boolean
                Флаг, который определяет, является ли очередь непрерывной (т.е
                должны ли слоты представляться последовательно в виде календаря)

            only_one_active - Boolean
                Флаг, который делает возможным иметь только одну предстоящую
                запись в очередь и позволяет, в момент её истечения, создать
                новую

            only_once - Boolean
                Флаг, который делает возможным записаться в очередь только один
                раз

        Взаимоотношения:
            slots - многие-к-одному
                Задает соответствие между очередью и её слотами
    '''

    __tablename__ = 'queues'
    name = Column(String, primary_key = True)
    title = Column(Text, nullable = False)
    description = Column(Text, nullable = False)
    duration = Column(Integer, nullable = False)
    waterfall = Column(Boolean, nullable = False, server_default = 'false')
    only_one_active = Column(Boolean, nullable = False,
                             server_default = 'false')
    only_once = Column(Boolean, nullable = False, server_default = 'false')

    slots = relationship('Slot', back_populates = 'queue')
