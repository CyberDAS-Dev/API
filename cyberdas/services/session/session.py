from .abstract_session import AbstractSession
from .сookie_serializable import CookieSerializable

from cyberdas.models import Session as SessionModel
from cyberdas.config import get_cfg
cfg = get_cfg()


class Session(AbstractSession, CookieSerializable):

    classname = SessionModel
    length = int(cfg['internal']['session.length'])
    cookie_name = 'SESSIONID'

    @classmethod
    def filter(cls, **ids):
        return {'sid': ids['sid']}
