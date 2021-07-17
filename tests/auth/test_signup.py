import pytest
from unittest.mock import ANY, MagicMock, patch

import falcon

from cyberdas.models import User

from conftest import (
    USER_EMAIL,
    USER_PASS,
    FACULTY_NAME,
    REGISTERED_USER_EMAIL,
)


class TestSignup:

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
        {"email": USER_EMAIL, "password": USER_PASS, "faculty": FACULTY_NAME},
        {"email": USER_EMAIL, "password": USER_PASS, "faculty": FACULTY_NAME,
         "name": "Иван", "patronymic": "Иванович"}
    ])
    def test_lacking_data_post(self, client, input_json):
        'При POST-запросе с недостаточными данными возвращается 400 Bad Request'
        resp = client.simulate_post(self.URI, json = input_json)
        assert resp.status == falcon.HTTP_400

    @pytest.mark.parametrize("input_json", [
        {"email": "badmail", "password": USER_PASS, "faculty": FACULTY_NAME,
         "name": "Иван", "surname": "Иванов"},
        {"email": USER_EMAIL, "password": 'bad', "faculty": FACULTY_NAME,
         "name": "Иван", "surname": "Иванов"},
        {"email": USER_EMAIL, "password": USER_PASS, "faculty": "bad",
         "name": "Иван", "surname": "Иванов"},
        {"email": REGISTERED_USER_EMAIL, "password": USER_PASS,
         "faculty": FACULTY_NAME, "name": "Иван", "surname": "Иванов"},
    ])
    def test_bad_data_post(self, client, input_json, oneUserDB):
        '''
        Если пользователь ввел:
        - некорректный адрес почты
        - слабый пароль
        - несуществующий факультет
        - уже зарегистрированную почту
        то, возвращается HTTP 400
        '''
        resp = client.simulate_post(self.URI, json = input_json)
        assert resp.status == falcon.HTTP_400

    @patch('cyberdas.services.SignupMail.send_verification', new = smtp_mock)
    def test_post(self, client, oneUserDB):
        '''
        Эндпоинт регистрации должен возвращать 200 OK в случае успеха, а так же
        отправлять письмо с валидным токеном.

        Отправка письма проверяется подменой метода send_verification из
        SignupMail и проверкой того, что он вызывался с нашим USER_EMAIL.
        Сам модуль отправки тестируется в test_mail.
        '''
        resp = client.simulate_post(
            self.URI,
            json = {
                "email": USER_EMAIL, "password": USER_PASS,
                "faculty": FACULTY_NAME, "name": "Иван", "surname": "Иванов"
            }
        )
        assert resp.status == falcon.HTTP_200
        self.smtp_mock.assert_called_once_with(ANY, USER_EMAIL)

    def test_user_added(self, oneUserDB):
        'После регистрации пользователь должен попасть в БД'
        with oneUserDB.session as dbses:
            user = dbses.query(User).filter_by(email = USER_EMAIL).first()
            assert user is not None
