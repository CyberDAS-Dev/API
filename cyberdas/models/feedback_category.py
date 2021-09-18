from sqlalchemy import (
    Column,
    String,
    ForeignKey,
)

from sqlalchemy.orm import relationship
from .__meta__ import Base

from cyberdas.utils.serializable_table import Serializable


class FeedbackCategory(Base, Serializable):
    '''
        Объект БД, хранящий информацию о категориях обратной связи.

        Поля:
            recipient_name - Primary key Foreign key String
                Имя получателя, к которому относится эта категория

            name - Primary key String
                Название категории

        Взаимоотношения:
            recipient - один-ко-многим
                Задает соответствие между категорией и получаетелем, к которому
                она относится
    '''

    __tablename__ = 'feedback_categories'
    recipient_name = Column(String, ForeignKey('recipients.name'),
                            primary_key = True)
    name = Column(String, primary_key = True)

    recipient = relationship('Recipient', back_populates = 'categories')
