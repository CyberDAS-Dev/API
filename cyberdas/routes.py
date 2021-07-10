from os import path
from .config import get_cfg

from .resources import * 
from .services import *

cfg = get_cfg()
mail = Mail(cfg)

testing = False
if 'cdci' in cfg:
    if (cfg['cdci']['build'] == 'test') or (cfg['cdci']['build'] == 'man'):
        testing = True

none = lambda *args: None

def route(api):
    '''
    Содержит все эндпоинты API.
    Каждая строка должна быть вида 'api.add_route(*route_uri*, *responding_resource*)'
    '''
    api.add_route('/signup', Signup(mail, testing))
    api.add_static_route('/', path.abspath('cyberdas/static/'))