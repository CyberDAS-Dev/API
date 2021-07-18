import pytest
import secrets
from datetime import datetime
from os import environ

from cyberdas.models import Session, Faculty, LongSession
from cyberdas.config import get_cfg


USER_EMAIL = 'user@cyberdas.net'
USER_PASS = 'some!stRong12'
REGISTERED_USER_EMAIL = 'second_user@das.net'
REGISTERED_USER_PASS = 'th!s1is_strong_too'
FACULTY_NAME = 'факультет'
SES_LENGTH = int(get_cfg()['internal']['session.length'])


@pytest.fixture(scope = 'class')
def oneUserDB(mockDB):
    '''
    База данных, содержащая одного уже зарегистрированного пользователя
    '''
    db = mockDB
    faculty = Faculty(id = 1, name = FACULTY_NAME)
    users = db.generate_users(1, [REGISTERED_USER_EMAIL], [REGISTERED_USER_PASS]) # noqa
    users[0].faculty = faculty
    db.setup_models(users)
    yield db


@pytest.fixture(scope = 'class')
def authorize(oneUserDB):
    sid = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    session = Session(uid = environ['AUTH_UID'], sid = sid,
                      csrf_token = csrf_token,
                      user_agent = 'curl', ip = '127.0.0.1',
                      expires = datetime(datetime.now().year + 1, 12, 31),
                      unsafe = False)
    oneUserDB.setup_models(session)
    yield {"SESSIONID": sid, "XCSRF-Token": csrf_token}


# должен быть реализован в виде функции, а не fixture, иначе будет исполняться
# одновременно с authorize при их одновременном использовании
def logout(oneUserDB):
    with oneUserDB.session as dbses:
        auth_ses = dbses.query(Session).filter_by(uid = environ['AUTH_UID']).all() # noqa
        for ses in auth_ses:
            dbses.delete(ses)


@pytest.fixture(scope = 'class')
def session(oneUserDB, authorize):
    yield authorize
    logout(oneUserDB)


@pytest.fixture(scope = 'class')
def long_authorize(oneUserDB, authorize):
    sid = authorize['SESSIONID']

    selector = secrets.token_urlsafe(12)
    validator = secrets.token_urlsafe(32)
    l_session = LongSession(uid = environ['AUTH_UID'], validator = validator,
                            selector = selector, associated_sid = sid,
                            expires = datetime(datetime.now().year + 1, 12, 31),
                            user_agent = 'curl', ip = '127.0.0.1')
    oneUserDB.setup_models(l_session)
    cookie = {"REMEMBER": f"{selector}:{validator}"}
    cookie.update(authorize)
    yield cookie


@pytest.fixture(scope = 'class')
def long_only_authorize(oneUserDB, long_authorize):
    cookie = long_authorize
    logout(oneUserDB)
    yield cookie


def long_logout(oneUserDB):
    logout(oneUserDB)
    with oneUserDB.session as dbses:
        long_session = dbses.query(LongSession).filter_by(uid = environ['AUTH_UID']).all() # noqa
        for ses in long_session:
            dbses.delete(ses)


@pytest.fixture(scope = 'class')
def long_session(oneUserDB, long_authorize):
    yield long_authorize
    long_logout(oneUserDB)


@pytest.fixture(scope = 'class')
def long_only_session(oneUserDB, long_only_authorize):
    yield long_only_authorize
    long_logout(oneUserDB)
