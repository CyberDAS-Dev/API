import pytest
from unittest.mock import ANY, MagicMock, patch

import falcon

from conftest import MockDB, generate_users
from cyberdas.services import SignupMail
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
                "email": USER_EMAIL, "password": "das",
                "faculty": "факультет", "name": "Иван", "surname": "Иванов"
            }
        )
        assert resp.status == falcon.HTTP_200
        self.smtp_mock.assert_called_once_with(ANY, USER_EMAIL)

    def test_user_added(self, oneUserDB):
        'После регистрации пользователь должен попасть в БД'
        with oneUserDB.session as dbses:
            user = dbses.query(User).filter_by(email = USER_EMAIL).first()
            assert user is not None


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


class TestResend:

    URI = '/resend'
    smtp_mock = MagicMock()

    def test_get(self, client):
        'Эндпоинт повторной отправки писем не отвечает на GET-запросы'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_no_data(self, client):
        'Если пользователь не отправил достаточно данных, возвращается HTTP 400'
        resp = client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_400

    def test_bad_email(self, client):
        '''
        Если пользователь указал некорректный эмэйл, возвращается HTTP 200,
        с формулировкой 'если такой пользователь найден, то письмо отправлено'
        '''
        resp = client.simulate_post(self.URI, json = {"email": "lol@das.net"})
        assert resp.status == falcon.HTTP_200

    @patch('cyberdas.services.SignupMail.send_verification', new = smtp_mock)
    def test_post(self, client, oneUserDB):
        'Если пользователь указал верный эмэйл, ему придет письмо с токеном'
        resp = client.simulate_post(self.URI,
                                    json = {"email": REGISTERED_USER_EMAIL})
        assert resp.status == falcon.HTTP_200
        self.smtp_mock.assert_called_once_with(ANY, REGISTERED_USER_EMAIL)

    @pytest.fixture
    def verified_user(self, oneUserDB):
        with oneUserDB.session as dbses:
            user = dbses.query(User).filter_by(email = REGISTERED_USER_EMAIL).first() # noqa
            user.email_verified = True
        yield
        with oneUserDB.session as dbses:
            user = dbses.query(User).filter_by(email = REGISTERED_USER_EMAIL).first() # noqa
            user.email_verified = False

    def test_verified_user(self, client, verified_user):
        '''
        Если уже верифицированный пользователь попросит переотправить письмо, то
        вернется ошибка
        '''
        resp = client.simulate_post(self.URI,
                                    json = {"email": REGISTERED_USER_EMAIL})
        assert resp.status == falcon.HTTP_403
