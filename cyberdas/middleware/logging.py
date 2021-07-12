import logging
from logging.config import fileConfig


class LoggerMiddleware(object):

    def __init__(self, cfg):
        '''
        Класс, содержащий логгирующий middleware. Для настройки логгирования
        испольузуется конфиг проекта (с синтаксисом стандартного питоновского
        logging-модуля).

        Аргументы:
            cfg(dict, необходим): Конфигурационный файл проекта (в обработанном
            виде).
        '''
        fileConfig(cfg, disable_existing_loggers = False)
        self.inspectionLogger = logging.getLogger('inspection')
        self.accessLogger = logging.getLogger('access')

    def process_resource(self, req, resp, resource, params):
        '''
        Автоматически вызывается Falcon при получении запроса.

        Добавляет возможность использовать inspection-логгер в контексте
        каждого запроса (req.context).
        '''
        req.context['logger'] = self.inspectionLogger

    def process_response(self, req, resp, resource, req_succeeded):
        '''
        Автоматически вызывается Falcon при возврате ответа на запрос.

        Оставляет записи в access-логах об обработанных запросах.
        '''
        uid = req.context.user.id if ('user' in req.context) else None
        data = {'method': req.method, 'uri': req.forwarded_uri,
                'ip': req.access_route[-1], 'agent': req.user_agent,
                'uid': uid, 'status': resp.status[:3]}
        if uid is None:
            message = "{method} {uri} {ip} {agent} {status}"
        else:
            message = "{method} {uri} id:{uid} {ip} {agent} {status}"
        self.accessLogger.info(message.format(**data))
