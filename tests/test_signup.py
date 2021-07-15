import pytest
from unittest.mock import MagicMock, patch

import falcon

from conftest import MockDB, generate_users
from cyberdas.models import User, Faculty
from cyberdas.config import get_cfg

USER_EMAIL = 'user@cyberdas.net'
REGISTERED_USER_EMAIL = 'second_user@das.net'


@pytest.fixture(scope='class')
def oneUserDB():
    '''
    База данных, содержащая одного уже зарегистрированного пользователя
    '''
    db = MockDB()
    faculty = Faculty(id = 1, name = 'факультет')
    users = generate_users(1, [REGISTERED_USER_EMAIL])
    users[0].faculty = faculty
    db.setup_models(users)
    return db


class TestSignup:

    cfg = get_cfg()
    URI = '/signup'
    smtp_mock = MagicMock()

    def test_get(self, client):
        'Регистрация не отвечает на GET-запросы'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_405

    @pytest.mark.parametrize("input_json", [
        {},
        {"email": "lol@mail.ru", "name": "Иван"},
        {"name": "Иван", "surname": "Иванов", "patronymic": "Иванович"},
        {"email": "lol@mail.ru", "password": "lol", "faculty": "факультет"},
        {"email": "lol@mail.ru", "password": "lol", "faculty": "факультет",
         "name": "Иван", "patronymic": "Иванович"}
    ])
    def test_lacking_data_post(self, client, input_json):
        'При POST-запросе с недостаточными данными возвращается 400 Bad Request'
        resp = client.simulate_post(self.URI, json = input_json)
        assert resp.status == falcon.HTTP_400

    def test_bad_email_post(self, client):
        'Если пользователь ввел некорректный адрес почты, возвращается HTTP 400'
        resp = client.simulate_post(
            self.URI,
            json = {
                "email": "badmail", "password": "lol", "faculty": "факультет",
                "name": "Иван", "surname": "Иванов"
            }
        )
        assert resp.status == falcon.HTTP_400

    def test_already_registered_post(self, client, oneUserDB):
        'Если пользователь ввел занятый адрес почты, возвращается HTTP 403'
        resp = client.simulate_post(
            self.URI,
            json = {
                "email": REGISTERED_USER_EMAIL, "password": "lol",
                "faculty": "факультет", "name": "Иван", "surname": "Иванов"
            }
        )
        assert resp.status == falcon.HTTP_403

    def test_bad_faculty_post(self, client, oneUserDB):
        'Если пользователь ввел занятый адрес почты, возвращается HTTP 403'
        resp = client.simulate_post(
            self.URI,
            json = {
                "email": "lol@mail.ru", "password": "lol",
                "faculty": "kek", "name": "Иван", "surname": "Иванов"
            }
        )
        assert resp.status == falcon.HTTP_400

    @patch('smtplib.SMTP', new = smtp_mock)
    def test_post(self, client, oneUserDB):
        '''
        Эндпоинт регистрации должен возвращать 200 OK в случае успеха, а так же
        отправлять письмо с валидным токеном.

        Отправка письма проверяется подменой smtplib.SMTP и проверкой того, что
        он вызывался. Сам модуль отправки тестируется в test_mail.
        '''
        resp = client.simulate_post(
            self.URI,
            json = {
                "email": USER_EMAIL, "password": "das",
                "faculty": "факультет", "name": "Иван", "surname": "Иванов"
            }
        )
        assert resp.status == falcon.HTTP_200
        self.smtp_mock.assert_called_once()

    def test_user_added(self, oneUserDB):
        'После регистрации пользователь должен попасть в БД'
        with oneUserDB.session as dbses:
            user = dbses.query(User).filter_by(email = USER_EMAIL).first()
            assert user is not None
