import pytest

from cyberdas.models import Session


# должен быть реализован в виде функции, а не fixture, иначе будет исполняться
# сразу при подключении
def logout(dbses):
    auth_ses = dbses.query(Session).filter_by(uid = 1).all()
    for ses in auth_ses:
        dbses.delete(ses)


@pytest.fixture(scope = 'class')
def session(auth, dbses):
    yield auth
    logout(dbses)
