import weakref

import falcon

from .routes import route
from .middlewares import middleware
from .config import get_cfg


class Service(falcon.App):

    __instance__ = None

    def __init__(self):
        self.__class__.__instance__ = weakref.proxy(self)
        self.cfg = get_cfg()
        super(Service, self).__init__()
        route(self)
        middleware(self)

    @classmethod
    def get_instance(cls):
        return cls.__instance__


api = application = Service()
