from datetime import datetime, date, timedelta

import falcon
from sqlalchemy import Date, cast

from cyberdas.models import Slot, Queue


class Collection:

    def on_get(self, req, resp, queueName):
        dbses = req.context.session

        day = req.get_param('day')
        offset = req.get_param('offset')
        if day is None and offset is not None:
            raise falcon.HTTPBadRequest(description = 'Отсутствует параметр day') # noqa

        slots = dbses.query(Slot).filter_by(queue_name = queueName)

        if day is not None and offset is None:
            day = date.fromisoformat(day)
            slots = slots.filter(cast(Slot.time, Date) == day)

        if day is not None and offset is not None:
            start = date.fromisoformat(day)
            end = start + timedelta(days = (int(offset) - 1))
            slots = slots.filter(cast(Slot.time, Date).between(start, end))

        resp.media = [slot.as_dict() for slot in slots.all()]
        resp.status = falcon.HTTP_200


class Item:

    def on_get(self, req, resp, queueName, slotId):
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
        dbses = req.context.session
        log = req.context.logger
        user = req.context.user

        slot = dbses.query(Slot).filter_by(queue_name = queueName,
                                           id = slotId).first()
        if slot is None:
            resp.status = falcon.HTTP_404
            return

        if slot.time < datetime.now():
            log.debug("[ИСТЁКШИЙ СЛОТ] uid %s, queueName %s, slotId %s"
                      % (user['uid'], queueName, slotId))
            raise falcon.HTTPForbidden(description = 'Слот истёк')

        if slot.user_id is not None:
            log.debug("[ЗАНЯТЫЙ СЛОТ] uid %s, queueName %s, slotId %s"
                      % (user['uid'], queueName, slotId))
            raise falcon.HTTPForbidden(description = 'Слот занят')

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
        dbses = req.context.session
        log = req.context.logger
        user = req.context.user

        slot = dbses.query(Slot).filter_by(queue_name = queueName,
                                           id = slotId).first()
        if slot is None:
            resp.status = falcon.HTTP_404
            return

        if slot.user_id != user['uid']:
            log.debug("[ЗАНЯТЫЙ СЛОТ] uid %s, queueName %s, slotId %s"
                      % (user['uid'], queueName, slotId))
            raise falcon.HTTPForbidden(
                description = 'Слот занят другим пользователем'
            )

        if slot.time < datetime.now():
            log.debug("[ИСТЁКШИЙ СЛОТ] uid %s, queueName %s, slotId %s"
                      % (user['uid'], queueName, slotId))
            raise falcon.HTTPForbidden(description = 'Слот истёк')

        slot.user_id = None
        log.info("[БРОНЬ УДАЛЕНА] uid %s, queueName %s, slotId %s"
                 % (user['uid'], queueName, slotId))
        resp.status = falcon.HTTP_204
