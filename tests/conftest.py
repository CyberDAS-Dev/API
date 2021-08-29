import pytest
import secrets
from os import environ
from datetime import datetime

from falcon import testing

from cyberdas.app import Service
from cyberdas.models import Session, Faculty

pytest_plugins = ['utils.mockDB']

environ['FACULTY_NAME'] = 'faculty'
environ['REGISTERED_USER_EMAIL'] = 'user@mail.com'


@pytest.fixture(scope = 'class')
def defaultDB(mockDB):
    '''
    База данных, содержащая двух зарегистрированных пользователя
    '''
    db = mockDB
    faculty = Faculty(id = 1, name = environ['FACULTY_NAME'])
    users = db.generate_users(2, [environ['REGISTERED_USER_EMAIL']])
    users[0].faculty = faculty
    users[1].faculty = faculty
    db.setup_models(users)
    yield db


@pytest.fixture(scope = 'class')
def dbses(defaultDB):
    with defaultDB.session as dbses:
        yield dbses


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
                      expires = datetime(datetime.now().year + 1, 12, 31))
    defaultDB.setup_models(session)
    environ['SESSIONID'] = sid
    environ['X-CSRF-Token'] = csrf_token
    yield {"SESSIONID": sid, "X-CSRF-Token": csrf_token}


class AuthorizedClient(testing.TestClient):

    def simulate_request(self, *args, **kwargs):
        return super().simulate_request(
            *args, **kwargs,
            cookies = {'SESSIONID': environ['SESSIONID']},
            headers = {'X-CSRF-Token': environ['X-CSRF-Token']}
        )


@pytest.fixture(scope = 'class')
def a_client(auth):
    yield AuthorizedClient(Service())
