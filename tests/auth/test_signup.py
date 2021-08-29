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

smtp_mock = MagicMock()


@patch('cyberdas.services.TransactionMail.send', new = smtp_mock)
class TestSender:

    URI = '/account/signup'

    def test_get(self, client):
        'Регистрация не отвечает на GET-запросы'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_405

    @pytest.mark.parametrize("input_json", [
        {},
        {"email": USER_EMAIL, "name": "Иван"},
        {"name": "Иван", "surname": "Иванов", "patronymic": "Иванович"},
        {"email": USER_EMAIL, "faculty_id": FACULTY_NAME},
        {"email": USER_EMAIL, "faculty_id": FACULTY_NAME,
         "name": "Иван", "patronymic": "Иванович"}
    ])
    def test_lacking_data(self, client, input_json):
        'При POST-запросе с недостаточными данными возвращается 400 Bad Request'
        resp = client.simulate_post(self.URI, json = input_json)
        assert resp.status == falcon.HTTP_400

    @pytest.mark.parametrize("input_json", [
        {"email": "badmail", "faculty_id": 1,
         "name": "Иван", "surname": "Иванов"},
        {"email": USER_EMAIL, "faculty_id": "bad",
         "name": "Иван", "surname": "Иванов"},
        {"email": REGISTERED_USER_EMAIL, "faculty_id": 1,
         "name": "Иван", "surname": "Иванов"},
    ])
    def test_bad_data(self, client, input_json, defaultDB):
        '''
        Если пользователь ввел:
        - некорректный адрес почты
        - несуществующий факультет
        то, возвращается HTTP 400

        В случае ввода уже зарегистрированной почты возвращается HTTP 403
        '''
        resp = client.simulate_post(self.URI, json = input_json)
        if input_json['email'] == REGISTERED_USER_EMAIL:
            assert resp.status == falcon.HTTP_403
        else:
            assert resp.status == falcon.HTTP_400

    def test_post(self, client, defaultDB):
        '''
        Эндпоинт регистрации должен возвращать 202 OK в случае успеха, а так же
        отправлять письмо с валидным токеном.

        Отправка письма проверяется подменой метода send из Mail и проверкой
        того, что он вызывался с нашим USER_EMAIL. Сам модуль отправки
        тестируется в test_mail.
        '''
        json = {"email": USER_EMAIL, "faculty_id": 1,
                "name": "Иван", "surname": "Иванов"}
        resp = client.simulate_post(self.URI, json = json)
        assert resp.status == falcon.HTTP_202
        smtp_mock.assert_called_with(ANY, USER_EMAIL, json)

    def test_user_not_created(self, dbses):
        'Пользователь в БД не создается до подтверждения с почты'
        user = dbses.query(User).filter_by(email = USER_EMAIL).first()
        assert user is None

    def test_data_is_stripped(self, client, defaultDB):
        '''
        Данные из пользовательских форм должны stripаться для предотвращения
        неверных результатов запросов к БД.
        '''
        json = {"email": '  ' + USER_EMAIL + '   ', "faculty_id": 1,
                "name": "Иван  ", "surname": "  Иванов  "}
        stripped_json = {"email": USER_EMAIL, "faculty_id": 1,
                         "name": "Иван", "surname": "Иванов"}
        resp = client.simulate_post(self.URI, json = json)
        assert resp.status == falcon.HTTP_202
        smtp_mock.assert_called_with(ANY, USER_EMAIL, stripped_json)


class TestValidate:

    URI = '/account/signup/validate'

    mail_args = {
        'sender': 'signup',
        'subject': 'Регистрация на CyberDAS',
        'template': 'signup',
        'frontend': 'https://cyberdas.net',
        'transaction': 'signup/validate',
        'expires': True
    }

    @pytest.fixture(scope = 'class')
    def token(self):
        mail = TransactionMail(cfg, **self.mail_args)
        json = {"email": USER_EMAIL, "faculty_id": 1,
                "name": "Иван", "surname": "Иванов"}
        yield mail.generate_token(json)

    @pytest.fixture(scope = 'class')
    def reg_token(self):
        mail = TransactionMail(cfg, **self.mail_args)
        json = {"email": REGISTERED_USER_EMAIL, "faculty_id": 1,
                "name": "Иван", "surname": "Иванов"}
        yield mail.generate_token(json)

    def test_post(self, client, token, dbses):
        'При отправке верного токена на эндпоинт создается пользователь'
        resp = client.simulate_get(self.URI, params = {'token': token})
        assert resp.status == falcon.HTTP_201
        user = dbses.query(User).filter_by(email = USER_EMAIL).first()
        assert user is not None

    def test_token_validation(self, client):
        'При отправке невалидного токена возвращается HTTP 403'
        resp = client.simulate_get(self.URI, params = {'token': '123'})
        assert resp.status == falcon.HTTP_403

    def test_registered_user(self, client, reg_token):
        'Уже зарегистрированным пользователям возвращается HTTP 403'
        resp = client.simulate_get(self.URI, params = {'token': reg_token})
        assert resp.status == falcon.HTTP_403
