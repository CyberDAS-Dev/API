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
from sqlalchemy.schema import ForeignKeyConstraint
from sqlalchemy_utils import EmailType
from .__meta__ import Base

from cyberdas.utils.serializable_table import Serializable


class Feedback(Base, Serializable):
    '''
        Объект БД, хранящий информацию об объектах обратной связи.

        Поля:
            recipient_name - Primary key Foreign key String
                Имя получателя, к которому направлено обращение

            id - Primary key Integer
                Уникальный идентификатор объекта

            category - Foreign key String
                Название категории, к которой относится обращение

            text - Text
                Содержание обращения

            email - Nullable EmailType
                Опциональное поле с адресом почты пользователя, отправившего
                обращение

            created_at - DateTime
                Хранит дату создания объекта
                Автоматически устанавливается БД с помощью SQL now()

        Взаимоотношения:
            recipient - один-ко-многим
                Задает соответствие между объектом обратной связи и её
                получаетелем
    '''

    __tablename__ = 'feedbacks'
    __table_args__ = (
        ForeignKeyConstraint(
            ['recipient_name', 'category'],
            ['feedback_categories.recipient_name', 'feedback_categories.name']
        ),
    )
    recipient_name = Column(String, ForeignKey('recipients.name'),
                            primary_key = True)
    id = Column(Integer, primary_key = True, autoincrement = True)
    category = Column(String, nullable = False)
    text = Column(Text, nullable = False)
    email = Column(EmailType, nullable = True)
    created_at = Column(DateTime, nullable = False, server_default = func.now())

    recipient = relationship('Recipient', back_populates = 'feedbacks')
