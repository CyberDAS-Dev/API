import string
import random
from os import environ

import falcon_sqla
import pytest
from sqlalchemy import create_engine

from cyberdas.models import Base, User
from cyberdas.config import get_cfg


@pytest.fixture(scope = "class")
def mockDB():
    yield MockDB(cleanup = environ.get('DB_CLEANUP', True))


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

    def _random_string(self, length = 10):
        letters = string.ascii_letters
        return (''.join(random.choice(letters) for i in range(length)))

    def _random_email(self):
        first = self._random_string(6)
        second = self._random_string(6)
        return first + "@" + second + '.com'

    def generate_users(self, n, emails = []):
        lst = []
        for x in range(1, n + 1):
            user = User(
                email = emails[x - 1] if len(emails) >= x else self._random_email(), # noqa
                name = self._random_string(), surname = self._random_string()
            )
            lst.append(user)
        return lst
