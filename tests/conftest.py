import string
import random
import pytest
from datetime import datetime

import falcon_sqla
from falcon import testing
from sqlalchemy import create_engine

from cyberdas.app import Service
from cyberdas.models import Base, User, Session
from cyberdas.config import get_cfg


@pytest.fixture(scope = 'class')
def client():
    yield testing.TestClient(Service())


def authorize(DB, uid):
    sid = random.randrange(10**5, 10**6)
    csrf_token = random.randrange(10**5, 10**6)
    session = Session(uid = uid, sid = sid,
                      csrf_token = csrf_token,
                      user_agent = 'curl', ip = '127.0.0.1',
                      expires = datetime(datetime.now().year + 1, 12, 31))
    DB.setup_models(session)
    return {"SESSIONID": sid, "XCSRF-Token": str(csrf_token)}


def logout(DB, uid):
    with DB.session as dbses:
        auth_ses = dbses.query(Session).filter_by(uid = uid).all()
        auth_ses.delete()


class MockDB(object):
    '''
    Интерфейс для доступа к базе данных, позволяющий легко очищать БД,
    добавлять модели и передавать коду внутренние интерфейсы БД.
    '''

    def __init__(self, cleanup = True):
        engine = create_engine(get_cfg()['alembic']['sqlalchemy.url'])
        self.manager = falcon_sqla.Manager(engine)
        if cleanup:
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)

    def setup_models(self, models):
        if type(models) != list:
            models = [models]
        with self.manager.session_scope() as session:
            for model in models:
                session.add(model)

    @property
    def session(self):
        return self.manager.session_scope()

    @property
    def middleware(self):
        return self.manager.middleware


def random_string(length = 10):
    letters = string.ascii_letters
    return (''.join(random.choice(letters) for i in range(length)))


def random_email():
    first = random_string(6)
    second = random_string(6)
    return first + "@" + second + '.com'


def generate_users(n, emails = [], passwords = []):
    lst = []
    for x in range(1, n + 1):
        user = User(
            email = emails[x - 1] if len(emails) >= x else random_email(),
            password = passwords[x - 1] if len(passwords) >= x else random_string(), # noqa
            name = random_string(), surname = random_string(),
            email_verified = False, verified = False
        )
        lst.append(user)
    return lst
