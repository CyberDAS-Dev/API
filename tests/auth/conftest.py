import pytest
import secrets
from datetime import datetime
from os import environ

from cyberdas.models import Session, Faculty
from cyberdas.config import get_cfg


USER_EMAIL = 'user@cyberdas.net'
REGISTERED_USER_EMAIL = 'second_user@cyberdas.net'
FACULTY_NAME = 'факультет'
SES_LENGTH = int(get_cfg()['internal']['session.length'])


@pytest.fixture(scope = 'class')
def oneUserDB(mockDB):
    '''
    База данных, содержащая одного уже зарегистрированного пользователя
    '''
    db = mockDB
    faculty = Faculty(id = 1, name = FACULTY_NAME)
    users = db.generate_users(1, [REGISTERED_USER_EMAIL]) # noqa
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
