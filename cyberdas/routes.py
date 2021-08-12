from os import path
from .config import get_cfg

from .resources import (
    Signup,
    Login,
    Logout,
    Refresh,
    Verify,
    Resend,
    Restore,
    queues,
    slots
)
from .services import (
    SignupMail,
    PassChecker,
    SessionManager
)

# Инициализация компонентов
cfg = get_cfg()
mail = SignupMail(cfg)
pass_checker = PassChecker()
session_manager = SessionManager()
###


def route(api):
    '''
    Содержит все эндпоинты API.
    Каждая строка должна быть вида `api.add_route([uri], [resource])`.
    '''
    api.add_route('/signup', Signup(mail, pass_checker))
    api.add_route('/login', Login(session_manager))
    api.add_route('/logout', Logout(session_manager))
    api.add_route('/refresh', Refresh(session_manager))
    api.add_route('/restore', Restore(session_manager))
    api.add_route('/verify', Verify(mail))
    api.add_route('/resend', Resend(mail))
    api.add_static_route('/', path.abspath('cyberdas/static/'))
    api.add_route('/queues', queues.Collection())
    api.add_route('/queues/{queueName}', queues.Item())
    api.add_route('/queues/{queueName}/slots', slots.Collection())
    api.add_route('/queues/{queueName}/slots/{slotId}', slots.Item())
    api.add_route('/queues/{queueName}/slots/{slotId}/reserve', slots.Reserve())
