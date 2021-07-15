from os import path
from .config import get_cfg

from .resources import (
    Signup,
    Login,
    Logout,
    Refresh,
)
from .services import (
    SignupMail,
)

cfg = get_cfg()
mail = SignupMail(cfg)


def route(api):
    '''
    Содержит все эндпоинты API.
    Каждая строка должна быть вида `api.add_route([uri], [resource])`.
    '''
    api.add_route('/signup', Signup(mail))
    api.add_route('/login', Login(cfg))
    api.add_route('/logout', Logout())
    api.add_route('/refresh', Refresh(cfg))
    api.add_static_route('/', path.abspath('cyberdas/static/'))
