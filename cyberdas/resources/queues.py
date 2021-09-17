import falcon

from cyberdas.models import Queue


class Collection:

    auth = {'disabled': 1}

    def on_get(self, req, resp):
        '''
        Возвращает список с информацией о всех имеющихся очередях
        '''
        dbses = req.context.session

        queues = dbses.query(Queue).all()

        resp.media = [queue.as_dict() for queue in queues]
        resp.status = falcon.HTTP_200


class Item:

    auth = {'disabled': 1}

    def on_get(self, req, resp, queue):
        '''
        Возвращает информацию об определенной очереди

        Параметры:

            queue (required, in: path) - имя запрашиваемой очереди
        '''
        dbses = req.context.session

        queue_obj = dbses.query(Queue).filter_by(name = queue).first()
        if queue_obj is None:
            resp.status = falcon.HTTP_404
            return

        resp.media = queue_obj.as_dict()
        resp.status = falcon.HTTP_200
