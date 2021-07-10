import falcon

from .routes import route
from .middlewares import middleware
from .config import get_cfg

class Service(falcon.App):
    def __init__(self):
        self.cfg = get_cfg()
        super(Service, self).__init__()
        route(self)
        middleware(self)

api = application = Service()
