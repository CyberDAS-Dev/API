import re
import pytest
import base64
from copy import copy

import falcon
from itsdangerous import URLSafeTimedSerializer

from conftest import MockDB, Service, generate_users
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


@pytest.fixture
def mockSMTP(smtpd):
    'Подмена SMTP сервера для отправки сообщений'
    api = Service.get_instance()
    mail_instance = api._router.find('/signup')[0].mail
    old_config = (
        copy(mail_instance.smtp_server), copy(mail_instance.smtp_port),
        copy(mail_instance.account_login), copy(mail_instance.account_password)
    )
    mail_instance.smtp_server = smtpd.hostname
    mail_instance.smtp_port = smtpd.port
    mail_instance.account_login = smtpd.config.login_username
    mail_instance.account_password = smtpd.config.login_password
    smtpd.config.use_starttls = True
    yield smtpd
    mail_instance.smtp_server = old_config[0]
    mail_instance.smtp_port = old_config[1]
    mail_instance.account_login = old_config[2]
    mail_instance.account_password = old_config[3]


class TestSignup:

    cfg = get_cfg()
    URI = '/signup'

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

    def test_post(self, client, oneUserDB, mockSMTP):
        '''
        Эндпоинт регистрации должен возвращать 200 OK в случае успеха, а так же
        отправлять письмо с валидным токеном.

        Вообще, эти тесты должны быть разделены, но скоуп у mockSMTP - функция,
        а у остальных моих fixture - класс, поэтому приходится размещать всё
        в одной функции.
        '''
        resp = client.simulate_post(
            self.URI,
            json = {
                "email": USER_EMAIL, "password": "das",
                "faculty": "факультет", "name": "Иван", "surname": "Иванов"
            }
        )
        assert resp.status == falcon.HTTP_200  # эндпоинт ответил
        assert len(mockSMTP.messages) == 1  # письмо пришло

        # валидность и наличие токена
        payload = mockSMTP.messages[0].get_payload()[0].get_payload()
        payload = base64.b64decode(payload.encode('utf-8')).decode('utf-8')
        r1 = re.findall(r'/verify\?[\w\=\.\-\_]+', payload)[0]
        r1 = r1.split('=')[1]

        mail_key = self.cfg['security']['secret.signup']
        mail_salt = self.cfg['security']['salt.signup']
        mail_expiry = int(self.cfg['mail']['expiry'])
        serializer = URLSafeTimedSerializer(mail_key)
        data = serializer.loads(r1, salt = mail_salt, max_age = mail_expiry)
        assert data

    def test_user_added(self, oneUserDB):
        with oneUserDB.session as dbses:
            user = dbses.query(User).filter_by(email = USER_EMAIL).first()
            assert user is not None
