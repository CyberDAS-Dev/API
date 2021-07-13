import pytest
import falcon
from datetime import datetime

from conftest import MockDB, generate_users, authorize
from cyberdas.models import Faculty, Session

USER_EMAIL = 'user@das.net'
USER_PASS = 'test'


@pytest.fixture(scope='class')
def oneUserDB():
    '''
    База данных, содержащая одного пользователя и один факультет
    '''
    db = MockDB()
    faculty = Faculty(id = 1, name = 'string')
    users = generate_users(1, [USER_EMAIL], [USER_PASS])
    users[0].faculty = faculty
    db.setup_models(users)
    return db


class TestLogin:

    URI = '/login'

    def test_get(self, client):
        'Логин не отвечает на GET-запросы'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_empty_post(self, client):
        'При пустом POST-запросе возвращается 400 Bad Request'
        resp = client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_400

    def test_bad_email(self, client, oneUserDB):
        'При вводе неверного эмэйла возвращается 401 Unauthorized'
        resp = client.simulate_post(self.URI, json = {'email': 'trash',
                                                      'password': USER_PASS})
        assert resp.status == falcon.HTTP_401

    def test_bad_password(self, client, oneUserDB):
        'При вводе неверного пароля возвращается 401 Unauthorized'
        resp = client.simulate_post(self.URI, json = {'email': USER_EMAIL,
                                                      'password': 'trash'})
        assert resp.status == falcon.HTTP_401

    @pytest.fixture(scope = 'class')
    def valid_post(self, client, oneUserDB):
        resp = client.simulate_post(self.URI, json = {'email': USER_EMAIL,
                                                      'password': USER_PASS})
        yield resp

    def test_post(self, valid_post):
        assert valid_post.status == falcon.HTTP_200

    def test_cookie(self, valid_post):
        assert 'SESSIONID' in valid_post.cookies

    def test_csrf_token(self, valid_post):
        assert 'antiCSRF' in valid_post.cookies

    @pytest.fixture(scope = 'class')
    def session_cookie(self, valid_post):
        yield valid_post.cookies['SESSIONID']

    def test_cookie_attributes(self, session_cookie):
        assert session_cookie.secure is True
        assert session_cookie.http_only is True

    def test_cookie_age(self, session_cookie):
        assert session_cookie.max_age == 15 * 60

    def test_session_created(self, session_cookie, oneUserDB):
        with oneUserDB.session as dbses:
            session = dbses.query(Session).filter_by(uid = 1).first()
            assert session is not None
            assert session.sid == session_cookie['SESSIONID']

    def test_two_sessions(self, client, oneUserDB):
        resp = client.simulate_post(self.URI, json = {'email': USER_EMAIL,
                                                      'password': USER_PASS})
        assert resp.status == falcon.HTTP_200
        with oneUserDB.session as dbses:
            sessions = dbses.query(Session).filter_by(uid = 1).all()
            assert len(sessions) == 2


class TestLogout:

    URI = '/logout'

    def test_post(self, client):
        'Логаут не отвечает на POST-запросы'
        resp = client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_unauthorized(self, client):
        'При попытке выйти не залогинившись, возвращается 401 Unauthorized'
        resp = client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_401

    def test_get(self, client, oneUserDB):
        '''
        При отправке GET-запроса пользователь получает обратно свой cookie, но
        просрочившийся в прошлом
        '''
        authorize(oneUserDB, 1)
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_200
        assert resp.cookies['SESSIONID'].expires <= datetime.now()
