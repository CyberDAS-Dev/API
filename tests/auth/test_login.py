import pytest

import falcon

from conftest import (
    REGISTERED_USER_EMAIL,
    REGISTERED_USER_PASS,
    SES_LENGTH,
)
from cyberdas.models import Session


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

    @pytest.mark.parametrize("input_json", [
        {"email": "bad@mail.com", "password": REGISTERED_USER_PASS},
        {"email": REGISTERED_USER_EMAIL, "password": 'bad'}
    ])
    def test_bad_data(self, client, oneUserDB, input_json):
        'При вводе неверного эмэйла или пароля возвращается 400 Bad Request'
        resp = client.simulate_post(self.URI, json = input_json)
        assert resp.status == falcon.HTTP_400

    @pytest.fixture(scope = 'class')
    def valid_post(self, client, oneUserDB):
        resp = client.simulate_post(self.URI,
                                    json = {'email': REGISTERED_USER_EMAIL,
                                            'password': REGISTERED_USER_PASS}
                                    )
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
        resp = client.simulate_post(self.URI,
                                    json = {'email': REGISTERED_USER_EMAIL,
                                            'password': REGISTERED_USER_PASS}
                                    )
        assert resp.status == falcon.HTTP_200
        with oneUserDB.session as dbses:
            sessions = dbses.query(Session).filter_by(uid = 1).all()
            assert len(sessions) == 2
