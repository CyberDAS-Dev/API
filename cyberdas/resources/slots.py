from datetime import datetime, date, timedelta

import falcon
from sqlalchemy import Date, cast

from cyberdas.models import Slot, Queue, User
from cyberdas.services import MailFactory, support_ott, auth_on_token
from cyberdas.utils.format_time import format_time


class Collection:

    auth = {'disabled': 1}

    def on_get(self, req, resp, queue):
        '''
        Возвращает список с информацией о имеющихся слотах в очереди

        Параметры:

            queue (required, in: path) - имя запрашиваемой очереди

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
        slots = dbses.query(Slot).filter_by(queue_name = queue)

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

    def on_get(self, req, resp, queue, id):
        '''
        Возвращает информацию об определенном слоте в очереди

        Параметры:

            queue (required, in: path) - имя запрашиваемой очереди

            id (required, in: path) - идентификатор запрашиваемого слота
        '''
        dbses = req.context.session

        slot = dbses.query(Slot).filter_by(queue_name = queue, id = id).first()
        if slot is None:
            resp.status = falcon.HTTP_404
            return

        resp.media = slot.as_dict()
        resp.status = falcon.HTTP_200


reserve_mail_args = {
    'sender': 'notify',
    'subject': 'Запись в очередь',
    'template': 'slot_reserve',
    'transaction': 'queues/{queue}/slots/{id}/reserve',
    'expires': False
}

delete_mail_args = {
    'sender': 'notify',
    'subject': 'Отмена записи в очередь',
    'template': 'slot_unreserve'
}


def send_notify_reserve(req, resp, resource):
    '''
    Отправляет уведомительное письмо о записи в очередь, при этом прикрепляя
    ссылку с токеном на отмену записи.

    Позволяет связать POST и DELETE для неаутентифицированных пользователей.
    '''
    if resp.status == falcon.HTTP_201:
        dbses = req.context.session
        uid = req.context.user['uid']
        mail_sender = resource.reserve_mail

        user = dbses.query(User).filter_by(id = uid).first()
        email = user.email
        data = {'email': email}
        transaction_url = req.path[1:]  # убираем слэш в начале
        template_data = {'queue_title': resp.context['queue_title'].lower(),
                         'slot_date': format_time(resp.context['slot_date'])}
        mail_sender.send(req, email, data, template_data = template_data,
                         transaction_url = transaction_url)


def send_notify_delete(req, resp, resource):
    '''
    Отправляет уведомление об отмене записи в очередь.
    '''
    if resp.status == falcon.HTTP_204:
        dbses = req.context.session
        uid = req.context.user['uid']
        mail_sender = resource.delete_mail

        user = dbses.query(User).filter_by(id = uid).first()
        queue = dbses.query(Queue).filter_by(name = resp.context['queue']).first() # noqa

        template_data = {'queue_title': queue.title.lower(),
                         'slot_date': format_time(resp.context['slot_date'])}
        mail_sender.send(user.email, req.context.logger,
                         template_data = template_data)


class Reserve:

    auth = {'disabled': 1}

    def __init__(self, mail_factory: MailFactory):
        self.reserve_mail = mail_factory.new_transaction(**reserve_mail_args)
        self.delete_mail = mail_factory.new_template(**delete_mail_args)

    def on_get(self, req, resp, queue, id):
        '''
        Перенаправляет пользователей, нажавших на ссылку для отмены записи в
        письме, на нужный метод (так как при нажатии на ссылку в письме браузер
        может послать только GET-запрос)
        '''
        if req.get_param('token'):
            self.on_delete(req, resp, queue, id)
        else:
            raise falcon.HTTPMethodNotAllowed(['POST', 'DELETE'])

    @falcon.before(support_ott)
    @falcon.after(send_notify_reserve)
    def on_post(self, req, resp, queue, id):
        '''
        Резервирует слот за пользователем. Не позволяет зарезервировать слоты,
        которые предназначались на уже прошедшее время.

        Параметры:

            queue (required, in: path) - имя запрашиваемой очереди

            id (required, in: path) - идентификатор запрашиваемого слота
        '''
        dbses = req.context.session
        log = req.context.logger
        user = req.context.user
        info = "uid %s, queue %s, id %s" % (user['uid'], queue, id)

        slot = dbses.query(Slot).filter_by(queue_name = queue, id = id).first()
        if slot is None:
            resp.status = falcon.HTTP_404
            return
        resp.context['slot_date'] = slot.time

        # Проверяем, не пытается ли пользователь забронировать `вчерашний` слот
        if slot.time < datetime.now():
            log.debug(f"[ИСТЁКШИЙ СЛОТ] {info}")
            raise falcon.HTTPForbidden(description = 'Слот истёк')

        # Проверяем, что слот свободен
        if slot.user_id is not None:
            log.debug(f"[ЗАНЯТЫЙ СЛОТ] {info}")
            raise falcon.HTTPForbidden(description = 'Слот занят')

        queue_obj = dbses.query(Queue).filter_by(name = queue).first()
        resp.context['queue_title'] = queue_obj.title
        if queue_obj.only_once or queue_obj.only_one_active:
            user_slots = dbses.query(Slot).filter_by(queue_name = queue,
                                                     user_id = user['uid'])
        # Для `only_once` очередей проверяем, что пользователь не имеет записей
        if queue_obj.only_once:
            if len(user_slots.all()) > 0:
                log.debug(f"[ONLY ONCE] {info}")
                raise falcon.HTTPForbidden(
                    description = 'Вы уже записались в эту очередь'
                )
        # Для `only_one_active` очередей проверяем, что пользователь не имеет
        # будущих записей
        if queue_obj.only_one_active:
            active_slots = user_slots.filter(Slot.time > datetime.now())
            if len(active_slots.all()) > 0:
                log.debug(f"[ONLY ONE ACTIVE] {info}")
                raise falcon.HTTPForbidden(
                    description = 'У вас уже есть предстоящая запись в эту очередь' # noqa
                )

        slot.user_id = user['uid']
        log.info(f"[БРОНЬ СОЗДАНА] {info}")
        resp.status = falcon.HTTP_201

    @falcon.before(auth_on_token('notify'))
    @falcon.after(send_notify_delete)
    def on_delete(self, req, resp, queue, id):
        '''
        Убирает резерв слота. Не позволяет убрать резерв со слотов, которые
        предназначались на уже прошедшее время.

        Параметры:

            queue (required, in: path) - имя запрашиваемой очереди

            id (required, in: path) - идентификатор запрашиваемого слота
        '''
        dbses = req.context.session
        log = req.context.logger
        user = req.context.user
        info = "uid %s, queue %s, id %s" % (user['uid'], queue, id)

        slot = dbses.query(Slot).filter_by(queue_name = queue, id = id).first()
        if slot is None:
            resp.status = falcon.HTTP_404
            return
        resp.context['slot_date'] = slot.time

        # Проверяем, вдруг слот свободен
        if slot.user_id is None:
            log.debug(f"[СВОБОДНЫЙ СЛОТ] {info}")
            resp.status = falcon.HTTP_404
            return

        # Пользователь не может разбронировать чужой слот
        if slot.user_id != user['uid']:
            log.debug(f"[ЗАНЯТЫЙ СЛОТ] {info}")
            raise falcon.HTTPForbidden(
                description = 'Слот занят другим пользователем'
            )

        # Проверяем, что пользователь не пытается разбронировать истёкший слот
        if slot.time < datetime.now():
            log.debug(f"[ИСТЁКШИЙ СЛОТ] {info}")
            raise falcon.HTTPForbidden(description = 'Слот истёк')

        slot.user_id = None
        log.info(f"[БРОНЬ УДАЛЕНА] {info}")
        resp.status = falcon.HTTP_204
        resp.context['queue'] = queue
