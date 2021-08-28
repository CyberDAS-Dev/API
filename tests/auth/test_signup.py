import pytest
from unittest.mock import ANY, MagicMock, patch
from os import environ

import falcon

from cyberdas.models import User
from cyberdas.services import TransactionMail
from cyberdas.config import get_cfg

USER_EMAIL = 'haha@mail.com'
FACULTY_NAME = environ['FACULTY_NAME']
REGISTERED_USER_EMAIL = environ['REGISTERED_USER_EMAIL']

cfg = get_cfg()


class TestSender:

    URI = '/signup'
    smtp_mock = MagicMock()

    def test_get(self, client):
        'Регистрация не отвечает на GET-запросы'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_405

    @pytest.mark.parametrize("input_json", [
        {},
        {"email": USER_EMAIL, "name": "Иван"},
        {"name": "Иван", "surname": "Иванов", "patronymic": "Иванович"},
        {"email": USER_EMAIL, "faculty": FACULTY_NAME},
        {"email": USER_EMAIL, "faculty": FACULTY_NAME,
         "name": "Иван", "patronymic": "Иванович"}
    ])
    def test_lacking_data(self, client, input_json):
        'При POST-запросе с недостаточными данными возвращается 400 Bad Request'
        resp = client.simulate_post(self.URI, json = input_json)
        assert resp.status == falcon.HTTP_400

    @pytest.mark.parametrize("input_json", [
        {"email": "badmail", "faculty": FACULTY_NAME,
         "name": "Иван", "surname": "Иванов"},
        {"email": USER_EMAIL, "faculty": FACULTY_NAME,
         "name": "Иван", "surname": "Иванов"},
        {"email": USER_EMAIL, "faculty": "bad",
         "name": "Иван", "surname": "Иванов"},
        {"email": REGISTERED_USER_EMAIL, "faculty": FACULTY_NAME,
         "name": "Иван", "surname": "Иванов"},
    ])
    def test_bad_data(self, client, input_json, defaultDB):
        '''
        Если пользователь ввел:
        - некорректный адрес почты
        - несуществующий факультет
        - уже зарегистрированную почту
        то, возвращается HTTP 400
        '''
        resp = client.simulate_post(self.URI, json = input_json)
        assert resp.status == falcon.HTTP_400

    @patch('cyberdas.services.TransactionMail.send', new = smtp_mock)
    def test_post(self, client, defaultDB):
        '''
        Эндпоинт регистрации должен возвращать 202 OK в случае успеха, а так же
        отправлять письмо с валидным токеном.

        Отправка письма проверяется подменой метода send из Mail и проверкой
        того, что он вызывался с нашим USER_EMAIL. Сам модуль отправки
        тестируется в test_mail.
        '''
        json = {"email": USER_EMAIL, "faculty": FACULTY_NAME,
                "name": "Иван", "surname": "Иванов"}
        resp = client.simulate_post(self.URI, json = json)
        assert resp.status == falcon.HTTP_202
        self.smtp_mock.assert_called_once_with(ANY, USER_EMAIL, json)

    def test_user_not_created(self, dbses):
        'Пользователь в БД не создается до подтверждения с почты'
        user = dbses.query(User).filter_by(email = USER_EMAIL).first()
        assert user is None


class TestValidate:

    URI = '/signup/validate'

    @pytest.fixture(scope = 'class')
    def token(self, mail):
        mail = TransactionMail(cfg, 'signup')
        json = {"email": USER_EMAIL, "faculty": FACULTY_NAME,
                "name": "Иван", "surname": "Иванов"}
        yield mail.generate_token(json)

    @pytest.fixture(scope = 'class')
    def reg_token(self, mail):
        mail = TransactionMail(cfg, 'signup')
        json = {"email": REGISTERED_USER_EMAIL, "faculty": FACULTY_NAME,
                "name": "Иван", "surname": "Иванов"}
        yield mail.generate_token(json)

    def test_post(self, client, token, dbses):
        'При отправке верного токена на эндпоинт создается пользователь'
        resp = client.simulate_get(self.URI, params = {'token': token})
        assert resp.status == falcon.HTTP_201
        user = dbses.query(User).filter_by(email = USER_EMAIL).first()
        assert user is not None

    def test_token_validation(self, client):
        'При отправке невалидного токена возвращается HTTP 400'
        resp = client.simulate_get(self.URI, params = {'token': '123'})
        assert resp.status == falcon.HTTP_400

    def test_user_not_replaced(self, client, reg_token):
        'Уже зарегистрированным пользователям возвращается HTTP 403'
        resp = client.simulate_get(self.URI, params = {'token': reg_token})
        assert resp.status == falcon.HTTP_403
