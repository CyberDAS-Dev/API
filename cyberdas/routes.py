from os import path
from .config import get_cfg

from .resources import (
    Signup,
    Login,
    Logout,
)
from .services import (
    Mail,
)

cfg = get_cfg()
mail = Mail(cfg)


def route(api):
    '''
    Содержит все эндпоинты API.
    Каждая строка должна быть вида `api.add_route([uri], [resource])`.
    '''
    api.add_route('/signup', Signup(mail))
    api.add_route('/login', Login(cfg))
    api.add_route('/logout', Logout())
    api.add_static_route('/', path.abspath('cyberdas/static/'))
