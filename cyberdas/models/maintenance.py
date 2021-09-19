from sqlalchemy import (
    Column,
    Text,
    String,
    Integer,
    ForeignKey,
    DateTime,
)

from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .__meta__ import Base

from cyberdas.utils.serializable_table import Serializable


class Maintenance(Base, Serializable):
    '''
        Объект БД, хранящий заявки на оказание технических услуг.

        Поля:
            id - Primary key Integer
                Уникальный идентификатор объекта

            category - Foreign key String
                Категория исполнителя, к которому направлено заявка

            building - Integer
                Корпус, в котором находится комната, на которую оставлена заявка

            room - Integer
                Комната, на которую оставлена заявка

            text - Text
                Содержание обращения

            user_id - Foreign key Integer
                Идентификатор пользователя, оставившего заявку

            created_at - DateTime
                Хранит дату создания объекта
                Автоматически устанавливается БД с помощью SQL now()

        Взаимоотношения:
            user - один-ко-многим
                Задает соответствие между заявкой и пользователем, её
                отправившим
    '''

    __tablename__ = 'maintenances'

    id = Column(Integer, primary_key = True)
    category = Column(String, nullable = False)
    building = Column(Integer, nullable = False)
    room = Column(Integer, nullable = False)
    text = Column(Text, nullable = False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable = False)
    created_at = Column(DateTime, nullable = False, server_default = func.now())

    user = relationship('User', back_populates = 'maintenances')
