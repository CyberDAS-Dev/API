from sqlalchemy import (
    Column,
    Text,
    String,
)

from sqlalchemy.orm import relationship
from sqlalchemy_utils import EmailType
from .__meta__ import Base

from cyberdas.utils.serializable_table import Serializable


class Recipient(Base, Serializable):
    '''
        Объект БД, хранящий информацию о получателях обратной связи.

        Поля:
            name - Primary key String
                Уникальный идентификатор, используемый для внутренних ссылок

            title - Text
                Человекочитаемое содержательное название получателя

            description - Text
                Описание получателя

            email - Nullable EmailType
                Необязательный адрес почты получателя, на который (если он
                указан) нужно пересылать обращения

        Взаимоотношения:
            feedbacks - многие-к-одному
                Задает соответствие между получателем и обращениями к нему

            categories - многие-к-одному
                Задает соответствие между получателем и его категориями
                обращений
    '''

    __tablename__ = 'recipients'
    name = Column(String, primary_key = True)
    title = Column(Text, nullable = False)
    description = Column(Text, nullable = False)
    email = Column(EmailType, nullable = True)

    feedbacks = relationship('Feedback', back_populates = 'recipient')
    categories = relationship('FeedbackCategory', back_populates = 'recipient')
