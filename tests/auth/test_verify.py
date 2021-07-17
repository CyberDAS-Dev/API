import pytest

import falcon

from cyberdas.services import SignupMail
from cyberdas.models import User
from cyberdas.config import get_cfg

from conftest import REGISTERED_USER_EMAIL


class TestVerify:

    URI = '/verify'
    redirect = 'cyberdas.net/verify'
    mail = SignupMail(get_cfg())

    def test_post(self, client):
        'Эндпоинт верификации не отвечает на POST-запросы'
        resp = client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_bad_token(self, client):
        'Если пользователь дал некорректный токен, возвращается HTTP 401'
        resp = client.simulate_get(self.URI, params = {"token": "badtoken"})
        assert resp.status == falcon.HTTP_401

    @pytest.fixture
    def deverify(self, oneUserDB):
        with oneUserDB.session as dbses:
            user = dbses.query(User).filter_by(email = REGISTERED_USER_EMAIL).first() # noqa
            user.email_verified = False

    @pytest.fixture
    def verify_token(self, deverify):
        token = self.mail.generate_token(REGISTERED_USER_EMAIL)
        yield token
        deverify

    @pytest.fixture
    def verify_token_redirect(self, deverify):
        token = self.mail.generate_token(REGISTERED_USER_EMAIL, self.redirect)
        yield token
        deverify

    def test_get(self, client, verify_token, oneUserDB):
        'При успешной верификации в БД устанавливается email_verified'
        resp = client.simulate_get(self.URI, params = {"token": verify_token})
        assert resp.status == falcon.HTTP_200
        with oneUserDB.session as dbses:
            user = dbses.query(User).filter_by(email = REGISTERED_USER_EMAIL).first() # noqa
            assert user.email_verified is True

    def test_get_redirect(self, client, verify_token_redirect):
        'Проверяет переадресацию при успешном запросе'
        resp = client.simulate_get(self.URI,
                                   params = {"token": verify_token_redirect})
        assert resp.status == falcon.HTTP_303
        assert resp.headers['location'] == self.redirect
