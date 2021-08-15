import pytest
import secrets
from os import environ
from datetime import datetime

from falcon import testing

from cyberdas.app import Service
from cyberdas.models import Session, Faculty

pytest_plugins = ['utils.mockDB']


@pytest.fixture(scope = 'class')
def defaultDB(mockDB):
    '''
    База данных, содержащая одного уже зарегистрированного пользователя
    '''
    db = mockDB
    faculty = Faculty(id = 1, name = 'faculty')
    users = db.generate_users(2, ['user@mail.com'])
    users[0].faculty = faculty
    users[1].faculty = faculty
    db.setup_models(users)
    yield db


@pytest.fixture(scope = 'class')
def client():
    yield testing.TestClient(Service())


@pytest.fixture(scope = 'class')
def auth(defaultDB):
    sid = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    session = Session(uid = environ.get('AUTH_UID', 1), sid = sid,
                      csrf_token = csrf_token,
                      user_agent = 'curl', ip = '127.0.0.1',
                      expires = datetime(datetime.now().year + 1, 12, 31),
                      unsafe = False)
    defaultDB.setup_models(session)
    environ['SESSIONID'] = sid
    environ['XCSRF-Token'] = csrf_token
    yield {"SESSIONID": sid, "XCSRF-Token": csrf_token}


class AuthorizedClient(testing.TestClient):

    def simulate_request(self, *args, **kwargs):
        return super().simulate_request(
            *args, **kwargs,
            cookies = {'SESSIONID': environ['SESSIONID']},
            headers = {'XCSRF-Token': environ['XCSRF-Token']}
        )


@pytest.fixture(scope = 'class')
def a_client(auth):
    yield AuthorizedClient(Service())
