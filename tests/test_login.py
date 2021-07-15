import pytest
import falcon

from conftest import MockDB, generate_users, authorize, logout
from cyberdas.models import Faculty, Session
from cyberdas.config import get_cfg

USER_EMAIL = 'user@das.net'
USER_PASS = 'test'
SES_LENGTH = int(get_cfg()['internal']['session.length'])


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
        resp = client.simulate_post(self.URI, json = {'email': 'trash@mail.ru',
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
        'Эндпоинт логина должен возвращать 200 OK в случае успеха'
        assert valid_post.status == falcon.HTTP_200

    def test_cookie(self, valid_post):
        'В ответе на запрос должен присутствовать Set-Cookie с SESSIONID'
        assert 'SESSIONID' in valid_post.cookies

    def test_csrf_token(self, valid_post):
        'В ответе на запрос должен присутствовать заголовок XCSRF-Token'
        assert 'XCSRF-token' in valid_post.headers

    @pytest.fixture(scope = 'class')
    def session_cookie(self, valid_post):
        yield valid_post.cookies['SESSIONID']

    def test_cookie_attributes(self, session_cookie):
        'Куки должен иметь параметры Secure, HttpOnly и SameSite (не покрыто)'
        assert session_cookie.secure is True
        assert session_cookie.http_only is True

    def test_cookie_age(self, session_cookie):
        'Время жизни куки должно быть таким же, как и в конфигурации проекта'
        assert session_cookie.max_age == SES_LENGTH

    def test_session_created(self, session_cookie, oneUserDB):
        'При успешном логине должна создаваться сессия в БД'
        with oneUserDB.session as dbses:
            session = dbses.query(Session).filter_by(uid = 1).first()
            assert session is not None
            assert session.sid == session_cookie.value

    def test_two_sessions(self, client, oneUserDB):
        'Если пользователь уже залогинен, то /login создает вторую сессию'
        resp = client.simulate_post(self.URI, json = {'email': USER_EMAIL,
                                                      'password': USER_PASS})
        assert resp.status == falcon.HTTP_200
        with oneUserDB.session as dbses:
            sessions = dbses.query(Session).filter_by(uid = 1).all()
            assert len(sessions) == 2


class TestLogout:

    URI = '/logout'

    @pytest.fixture(scope = 'class')
    def session(self, oneUserDB):
        yield authorize(oneUserDB, 1)

    def test_unauthorized(self, client):
        'При попытке выйти не залогинившись, возвращается 401 Unauthorized'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_401

    def test_post(self, client, session):
        'Логаут не отвечает на POST-запросы'
        resp = client.simulate_post(
            self.URI,
            cookies = {'SESSIONID': session['SESSIONID']},
            headers = {'XCSRF-Token': session['XCSRF-Token']}
        )
        assert resp.status == falcon.HTTP_405

    def test_get(self, client, session):
        '''
        При отправке GET-запроса пользователь получает обратно свой cookie, но
        просрочившийся в прошлом
        '''
        resp = client.simulate_get(
            self.URI,
            cookies = {'SESSIONID': session['SESSIONID']}
        )
        assert resp.status == falcon.HTTP_200
        assert resp.cookies['SESSIONID'].max_age == -1

    def test_clean_db(self, oneUserDB):
        'При логауте сессия должна удаляться из БД'
        with oneUserDB.session as dbses:
            session = dbses.query(Session).filter_by(uid = 1).first()
            assert session is None


class TestRefresh:

    URI = '/refresh'

    @pytest.fixture(scope = 'class')
    def session(self, oneUserDB):
        yield authorize(oneUserDB, 1)
        logout(oneUserDB, 1)

    def test_unauthorized(self, client):
        'При попытке продлить не залогинившись, возвращается 401 Unauthorized'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_401

    def test_post(self, client, session):
        'Рефреш не отвечает на POST-запросы'
        resp = client.simulate_post(
            self.URI,
            cookies = {'SESSIONID': session['SESSIONID']},
            headers = {'XCSRF-Token': session['XCSRF-Token']}
        )
        assert resp.status == falcon.HTTP_405

    def test_get(self, client, session):
        '''
        При отправке GET-запроса пользователь получает обратно свой cookie,
        срок действия которого продлен на длительность одной сессии
        '''
        resp = client.simulate_get(
            self.URI,
            cookies = {'SESSIONID': session['SESSIONID']}
        )
        assert resp.status == falcon.HTTP_200
        assert resp.cookies['SESSIONID'].max_age == SES_LENGTH
