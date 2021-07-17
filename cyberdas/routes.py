from os import path
from .config import get_cfg

from .resources import (
    Signup,
    Login,
    Logout,
    Refresh,
    Verify,
    Resend,
)
from .services import (
    SignupMail,
    PassChecker
)

cfg = get_cfg()
mail = SignupMail(cfg)
pass_checker = PassChecker()


def route(api):
    '''
    Содержит все эндпоинты API.
    Каждая строка должна быть вида `api.add_route([uri], [resource])`.
    '''
    api.add_route('/signup', Signup(mail, pass_checker))
    api.add_route('/login', Login(cfg))
    api.add_route('/logout', Logout())
    api.add_route('/refresh', Refresh(cfg))
    api.add_route('/verify', Verify(mail))
    api.add_route('/resend', Resend(mail))
    api.add_static_route('/', path.abspath('cyberdas/static/'))
