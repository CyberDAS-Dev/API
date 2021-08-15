from os import path
from .config import get_cfg

from .resources import (
    queues,
    slots
)
from .services import (
    SignupMail,
    SessionManager
)

# Инициализация компонентов
cfg = get_cfg()
mail = SignupMail(cfg)
session_manager = SessionManager()
###


def route(api):
    '''
    Содержит все эндпоинты API.
    Каждая строка должна быть вида `api.add_route([uri], [resource])`.
    '''
    api.add_static_route('/', path.abspath('cyberdas/static/'))
    api.add_route('/queues', queues.Collection())
    api.add_route('/queues/{queueName}', queues.Item())
    api.add_route('/queues/{queueName}/slots', slots.Collection())
    api.add_route('/queues/{queueName}/slots/{slotId}', slots.Item())
    api.add_route('/queues/{queueName}/slots/{slotId}/reserve', slots.Reserve())
