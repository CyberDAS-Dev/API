import json
from os import path

import falcon
from falcon.media.validators import jsonschema

from cyberdas.models import Recipient, Feedback, FeedbackCategory


def _format_recipient(rcp_dict, rcp_obj):
    'Скрывает адрес почты получателя и разворачивает категории в массив строк'
    new_dict = {'name': rcp_dict['name'], 'title': rcp_dict['title'],
                'description': rcp_dict['description']}
    new_dict['categories'] = [ctg.name for ctg in rcp_obj.categories]
    return new_dict


class RecipientCollection:

    auth = {'disabled': 1}

    def on_get(self, req, resp):
        '''
        Возвращает список с информацией о всех имеющихся получателях обращений
        '''
        dbses = req.context.session

        recipients = dbses.query(Recipient).all()

        resp.media = [_format_recipient(rcp.as_dict(), rcp) for rcp in recipients] # noqa
        resp.status = falcon.HTTP_200


class RecipientItem:

    auth = {'disabled': 1}

    def on_get(self, req, resp, recipient):
        '''
        Возвращает информацию об определенном получателе

        Параметры:
            recipient (required, in: path) - имя получателя
        '''
        dbses = req.context.session

        rcp_obj = dbses.query(Recipient).filter_by(name = recipient).first()
        if rcp_obj is None:
            raise falcon.HTTPNotFound()

        resp.media = _format_recipient(rcp_obj.as_dict(), rcp_obj)
        resp.status = falcon.HTTP_200


class FeedbackCollection:

    auth = {'disabled': 1}

    with open(path.abspath('cyberdas/static/feedback_schema.json'), 'r') as f:
        feedback_schema = json.load(f)

    @jsonschema.validate(feedback_schema)
    def on_post(self, req, resp, recipient):
        '''
        Создает новый объект обратной связи для получателя

        Параметры:
            recipient (required, in: path) - имя получателя

            category (required, in: body) - категория обращения, из доступных
                у этого отправителя

            text (required, in: body) - содержание обращения

            email (optional, in: body) - необязательный адрес почты отправителя
                для получения ответа
        '''
        dbses = req.context.session
        log = req.context.logger

        # Проверяем, что получатель существует
        if dbses.query(Recipient).filter_by(name = recipient).first() is None:
            raise falcon.HTTPNotFound()

        # Получаем пользовательские данные
        data = req.get_media()

        # Проверяем, что категория существует
        category = dbses.query(FeedbackCategory).filter_by(
            recipient_name = recipient,
            name = data['category']
        ).first()
        if category is None:
            raise falcon.HTTPBadRequest(
                description = 'Указанной категории не существует'
            )

        # Добавляем обращение в базу данных
        new_item = Feedback(recipient_name = recipient, **data)
        dbses.add(new_item)
        dbses.flush()

        log.info('[FEEDBACK][НОВЫЙ] recipient %s, category %s, id %s'
                 % (recipient, data['category'], new_item.id))
        resp.status = falcon.HTTP_201
