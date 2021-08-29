import pytest
from unittest.mock import ANY, MagicMock, patch
from os import environ

import falcon

from cyberdas.models import Session
from cyberdas.services import TransactionMail
from cyberdas.config import get_cfg

cfg = get_cfg()

USER_EMAIL = 'haha@mail.com'
FACULTY_NAME = environ['FACULTY_NAME']
REGISTERED_USER_EMAIL = environ['REGISTERED_USER_EMAIL']
SES_LENGTH = int(get_cfg()['internal']['session.length'])

smtp_mock = MagicMock()


@patch('cyberdas.services.TransactionMail.send', new = smtp_mock)
class TestSender:

    URI = '/account/login'

    def test_get(self, client):
        'Логин не отвечает на GET-запросы'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_lacking_data(self, client):
        'При пустом POST-запросе возвращается 400 Bad Request'
        resp = client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_400

    def test_bad_data(self, client):
        '''
        При вводе не-эмэйла возвращается HTTP 400
        '''
        resp = client.simulate_post(self.URI, json = {"email": "lol123"})
        assert resp.status == falcon.HTTP_400

    def test_unregistered_user(self, client):
        '''
        При вводе незарегистрированного эмэйла возвращается HTTP 403
        '''
        resp = client.simulate_post(self.URI, json = {"email": USER_EMAIL})
        assert resp.status == falcon.HTTP_403

    def test_post(self, client, defaultDB):
        '''
        Эндпоинт логина должен возвращать 202 OK в случае успеха, а так же
        отправлять письмо с валидным токеном.

        Отправка письма проверяется подменой метода send из Mail и проверкой
        того, что он вызывался с нашим USER_EMAIL. Сам модуль отправки
        тестируется в test_mail.
        '''
        json = {"email": REGISTERED_USER_EMAIL}
        resp = client.simulate_post(self.URI, json = json)
        json['uid'] = 1  # автодобавление айди
        assert resp.status == falcon.HTTP_202
        smtp_mock.assert_called_with(ANY, REGISTERED_USER_EMAIL, json)

    def test_session_not_created(self, dbses):
        'Сессия в БД не создается до подтверждения с почты'
        ses = dbses.query(Session).filter_by(uid = 1).first()
        assert ses is None

    def test_data_is_stripped(self, client, defaultDB):
        '''
        Данные из пользовательских форм должны stripаться для предотвращения
        неверных результатов запросов к БД.
        '''
        json = {"email": '  ' + REGISTERED_USER_EMAIL + '   '}
        stripped_json = {"email": REGISTERED_USER_EMAIL}
        resp = client.simulate_post(self.URI, json = json)
        stripped_json['uid'] = 1  # автодобавление айди
        assert resp.status == falcon.HTTP_202
        smtp_mock.assert_called_with(ANY, REGISTERED_USER_EMAIL, stripped_json)


class TestValidate:

    URI = '/account/login/validate'

    mail_args = {
        'sender': 'signup',
        'subject': 'Вход в аккаунт на CyberDAS',
        'template': 'login',
        'frontend': 'https://cyberdas.net',
        'transaction': 'login/validate',
        'expires': True
    }

    @pytest.fixture(scope = 'class')
    def token(self):
        mail = TransactionMail(cfg, **self.mail_args)
        json = {"email": USER_EMAIL}
        yield mail.generate_token(json)

    def test_token_validation(self, client):
        'При отправке невалидного токена возвращается HTTP 403'
        resp = client.simulate_get(self.URI, params = {'token': '123'})
        assert resp.status == falcon.HTTP_403

    @pytest.fixture(scope = 'class')
    def reg_token(self):
        mail = TransactionMail(cfg, **self.mail_args)
        json = {"email": REGISTERED_USER_EMAIL, "uid": 1}
        yield mail.generate_token(json)

    @pytest.fixture(scope = 'class')
    def valid_post(self, client, reg_token, defaultDB):
        resp = client.simulate_get(self.URI, params = {'token': reg_token})
        yield resp

    def test_post(self, valid_post):
        'При отправке верного токена эндпоинт возвращает HTTP 201'
        assert valid_post.status == falcon.HTTP_201

    def test_cookie(self, valid_post):
        'В ответе на запрос должен присутствовать Set-Cookie с SESSIONID'
        assert 'SESSIONID' in valid_post.cookies

    def test_csrf_token(self, valid_post):
        'В ответе на запрос должен присутствовать заголовок X-CSRF-Token'
        assert 'X-CSRF-Token' in valid_post.headers

    @pytest.fixture(scope = 'class')
    def session_cookie(self, valid_post):
        yield valid_post.cookies['SESSIONID']

    def test_ses_created(self, valid_post, dbses, session_cookie):
        'При отправке верного токена на эндпоинт создается сессия'
        ses = dbses.query(Session).filter_by(uid = 1).first()
        assert ses is not None
        assert ses.sid == session_cookie.value

    def test_cookie_attributes(self, session_cookie):
        'Куки должен иметь параметры Secure, HttpOnly и SameSite (не покрыто)'
        assert session_cookie.secure is True
        assert session_cookie.http_only is True

    def test_cookie_age(self, session_cookie):
        'Время жизни куки должно быть таким же, как и в конфигурации проекта'
        assert session_cookie.max_age == SES_LENGTH

    def test_two_sessions(self, client, reg_token, dbses):
        'Если пользователь уже залогинен, то создается вторая сессия'
        resp = client.simulate_get(self.URI, params = {'token': reg_token})
        assert resp.status == falcon.HTTP_201
        sessions = dbses.query(Session).filter_by(uid = 1).all()
        assert len(sessions) == 2
