from os import path
from .config import get_cfg

from .resources import (
    Signup,
)
from .services import (
    Mail,
)

cfg = get_cfg()
mail = Mail(cfg)


def none(*args):
    return None


testing = False
if 'cdci' in cfg:
    if (cfg['cdci']['build'] == 'test') or (cfg['cdci']['build'] == 'man'):
        testing = True


def route(api):
    '''
    Содержит все эндпоинты API.
    Каждая строка должна быть вида `api.add_route([uri], [resource])`.
    '''
    api.add_route('/signup', Signup(mail, testing))
    api.add_static_route('/', path.abspath('cyberdas/static/'))
