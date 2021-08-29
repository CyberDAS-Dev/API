from datetime import datetime, date, timedelta

import falcon
from sqlalchemy import Date, cast

from cyberdas.models import Slot, Queue


class Collection:

    auth = {'disabled': 1}

    def on_get(self, req, resp, queueName):
        '''
        Возвращает список с информацией о имеющихся слотах в очереди

        Параметры:

            queueName (required, in: path) - имя запрашиваемой очереди

            day (optional, in: query) - если представлен без параметра offset,
                то возвращается информацию о слотах только за указанный день;
                вместе с параметром offset используется для составления запроса
                на слоты за промежуток дат

            offset (optional, in: query) - длина интервала дат за которые
                необходимо предоставить информацию о слотах, в днях

            my (optional, in: query) - возвращать только слоты пользователя,
                сделавшего запрос
        '''
        dbses = req.context.session

        # Получаем параметры и проверяем ввод от пользователя
        day = req.get_param('day')
        offset = req.get_param('offset')
        my = req.get_param_as_bool('my')
        if day is None and offset is not None:
            raise falcon.HTTPBadRequest(description = 'Отсутствует параметр day') # noqa

        if offset is not None and (int(offset) < 1 or int(offset) > 90):
            raise falcon.HTTPBadRequest(description = 'Offset принимает значения от 1 до 90') # noqa

        # Базовый запрос - если нет параметров, то вернутся все слоты из очереди
        slots = dbses.query(Slot).filter_by(queue_name = queueName)

        # Если предоставлен только day, возвращаем слоты за указанный день
        if day is not None and offset is None:
            day = date.fromisoformat(day)
            slots = slots.filter(cast(Slot.time, Date) == day)

        # Если предоставлен day и offset, возвращаем слайс слотов
        if day is not None and offset is not None:
            start = date.fromisoformat(day)
            end = start + timedelta(days = (int(offset) - 1))
            slots = slots.filter(cast(Slot.time, Date).between(start, end))

        # Если есть флаг `my`, оставляем только слоты пользователя
        if my:
            if req.context.user:
                slots = slots.filter_by(user_id = req.context.user['uid'])
            else:
                raise falcon.HTTPUnauthorized()

        resp.media = [slot.as_dict() for slot in slots.all()]
        resp.status = falcon.HTTP_200


class Item:

    auth = {'disabled': 1}

    def on_get(self, req, resp, queueName, slotId):
        '''
        Возвращает информацию об определенном слоте в очереди

        Параметры:

            queueName (required, in: path) - имя запрашиваемой очереди

            slotId (required, in: path) - идентификатор запрашиваемого слота
        '''
        dbses = req.context.session

        slot = dbses.query(Slot).filter_by(queue_name = queueName,
                                           id = slotId).first()
        if slot is None:
            resp.status = falcon.HTTP_404
            return

        resp.media = slot.as_dict()
        resp.status = falcon.HTTP_200


class Reserve:

    def on_post(self, req, resp, queueName, slotId):
        '''
        Резервирует слот за пользователем. Не позволяет зарезервировать слоты,
        которые предназначались на уже прошедшее время.

        Параметры:

            queueName (required, in: path) - имя запрашиваемой очереди

            slotId (required, in: path) - идентификатор запрашиваемого слота
        '''
        dbses = req.context.session
        log = req.context.logger
        user = req.context.user

        slot = dbses.query(Slot).filter_by(queue_name = queueName,
                                           id = slotId).first()
        if slot is None:
            resp.status = falcon.HTTP_404
            return

        # Проверяем, не пытается ли пользователь забронировать `вчерашний` слот
        if slot.time < datetime.now():
            log.debug("[ИСТЁКШИЙ СЛОТ] uid %s, queueName %s, slotId %s"
                      % (user['uid'], queueName, slotId))
            raise falcon.HTTPForbidden(description = 'Слот истёк')

        # Проверяем, что слот свободен
        if slot.user_id is not None:
            log.debug("[ЗАНЯТЫЙ СЛОТ] uid %s, queueName %s, slotId %s"
                      % (user['uid'], queueName, slotId))
            raise falcon.HTTPForbidden(description = 'Слот занят')

        # Для `only_once` очередей проверяем, что пользователь не занимал другие слоты # noqa
        queue = dbses.query(Queue).filter_by(name = queueName).first()
        if queue.only_once:
            user_slots = dbses.query(Slot).filter_by(queue_name = queueName,
                                                     user_id = user['uid'])
            if len(user_slots.all()) > 0:
                log.debug("[ONLY ONCE] uid %s, queueName %s, slotId %s"
                          % (user['uid'], queueName, slotId))
                raise falcon.HTTPForbidden(
                    description = 'Вы уже записались в эту очередь'
                )

        slot.user_id = user['uid']
        log.info("[БРОНЬ СОЗДАНА] uid %s, queueName %s, slotId %s"
                 % (user['uid'], queueName, slotId))
        resp.status = falcon.HTTP_201

    def on_delete(self, req, resp, queueName, slotId):
        '''
        Убирает резерв слота. Не позволяет убрать резерв со слотов, которые
        предназначались на уже прошедшее время.

        Параметры:

            queueName (required, in: path) - имя запрашиваемой очереди

            slotId (required, in: path) - идентификатор запрашиваемого слота
        '''
        dbses = req.context.session
        log = req.context.logger
        user = req.context.user

        slot = dbses.query(Slot).filter_by(queue_name = queueName,
                                           id = slotId).first()
        if slot is None:
            resp.status = falcon.HTTP_404
            return

        # Проверяем, вдруг слот свободен
        if slot.user_id is None:
            log.debug("[СВОБОДНЫЙ СЛОТ] uid %s, queueName %s, slotId %s"
                      % (user['uid'], queueName, slotId))
            resp.status = falcon.HTTP_404
            return

        # Пользователь не может разбронировать чужой слот
        if slot.user_id != user['uid']:
            log.debug("[ЗАНЯТЫЙ СЛОТ] uid %s, queueName %s, slotId %s"
                      % (user['uid'], queueName, slotId))
            raise falcon.HTTPForbidden(
                description = 'Слот занят другим пользователем'
            )

        # Проверяем, что пользователь не пытается разбронировать истёкший слот
        if slot.time < datetime.now():
            log.debug("[ИСТЁКШИЙ СЛОТ] uid %s, queueName %s, slotId %s"
                      % (user['uid'], queueName, slotId))
            raise falcon.HTTPForbidden(description = 'Слот истёк')

        slot.user_id = None
        log.info("[БРОНЬ УДАЛЕНА] uid %s, queueName %s, slotId %s"
                 % (user['uid'], queueName, slotId))
        resp.status = falcon.HTTP_204
