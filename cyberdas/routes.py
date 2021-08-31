from os import path
from .config import get_cfg

from .resources import (
    queues,
    slots,
    signup,
    login,
    logout,
)
from .services import (
    TransactionMailFactory,
    SessionManager,
)

# Инициализация компонентов
cfg = get_cfg()
mail_factory = TransactionMailFactory(cfg)
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
    api.add_route('/queues/{queueName}/slots/{slotId}/reserve',
                  slots.Reserve(mail_factory))
    api.add_route('/account/signup', signup.Sender(mail_factory))
    api.add_route('/account/signup/validate', signup.Validator(mail_factory))
    api.add_route('/account/login', login.Sender(mail_factory))
    api.add_route('/account/login/validate', login.Validator(mail_factory,
                                                             session_manager))
    api.add_route('/account/logout', logout.Logout(session_manager))
