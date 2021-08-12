import falcon

from cyberdas.models import Queue


class Collection:

    def on_get(self, req, resp):
        '''
        Возвращает список с информацией о всех имеющихся очередях
        '''
        dbses = req.context.session

        queues = dbses.query(Queue).all()

        resp.media = [queue.as_dict() for queue in queues]
        resp.status = falcon.HTTP_200


class Item:

    def on_get(self, req, resp, queueName):
        '''
        Возвращает информацию об определенной очереди

        Параметры:

            queueName (required, in: path) - имя запрашиваемой очереди
        '''
        dbses = req.context.session

        queue = dbses.query(Queue).filter_by(name = queueName).first()
        if queue is None:
            resp.status = falcon.HTTP_404
            return

        resp.media = queue.as_dict()
        resp.status = falcon.HTTP_200
