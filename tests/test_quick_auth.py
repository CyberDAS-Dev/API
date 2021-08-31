import pytest
from os import environ
from unittest.mock import MagicMock, patch

import falcon

from cyberdas.services import quick_auth
from cyberdas.services.mail import Mail
from cyberdas.models import User
from cyberdas.config import get_cfg

AUTHENTICATED_CONTEXT = {'lol': 1}

do_quick_auth = quick_auth._get_or_add_user
cfg = get_cfg()


class Context:

    def __init__(self, dbses, user = None):
        self.user = user
        self.session = dbses
        self.logger = MagicMock()

    def __getitem__(self, key):
        return self.__dict__.__getitem__(key)

    def __setitem__(self, key, value):
        return self.__dict__.__setitem__(key, value)


class MockReq:

    def __init__(self, dbses, user = None, json_data = None, token = None):
        self.context = Context(dbses, user)
        self.json_data = json_data
        self.token = token

    def get_media(self, *args, **kwargs):
        return self.json_data

    def get_param(self, name, required = False, *args, **kwargs):
        if name == 'token':
            if self.token is None and required:
                raise falcon.HTTPBadRequest()
            return self.token


@pytest.fixture()
def req(dbses):
    yield MockReq(dbses)


@pytest.fixture()
def auth_req(dbses):
    yield MockReq(dbses, user = AUTHENTICATED_CONTEXT)


class TestQuickAuth:

    def test_lacking_data(self, req):
        'При отсутствии данных в запросе возвращается HTTP 401'
        data = dict()
        with pytest.raises(falcon.HTTPUnauthorized):
            do_quick_auth(req, data)

    def test_login_bad_data(self, req):
        'При вводе не-эмэйла возвращается HTTP 401'
        data = {'email': 'lol'}
        with pytest.raises(falcon.HTTPUnauthorized):
            do_quick_auth(req, data)

    def test_login_unregistered(self, req):
        'При вводе незарегистрированного эмэйла возвращается HTTP 401'
        data = {'email': 'hello@user.name'}
        with pytest.raises(falcon.HTTPUnauthorized):
            do_quick_auth(req, data)

    def test_login(self, req):
        'При вводе существующего в базе эмэйла в контекст запроса попадает uid'
        data = {'email': environ['REGISTERED_USER_EMAIL']}
        do_quick_auth(req, data)
        assert req.context['user'] == {'uid': 1}

    @pytest.mark.parametrize("data", [
        {"email": "badmail", "faculty_id": 1,
         "name": "Иван", "surname": "Иванов"},
        {"email": "hello@name.mail", "faculty_id": "bad",
         "name": "Иван", "surname": "Иванов"},
        {"faculty_id": 1, "name": "Иван", "surname": "Иванов"},
        {"email": "hello@name.mail", "name": "Иван", "surname": "Иванов"},
    ])
    def test_signup_bad_data(self, req, data):
        '''
        При вводе некорректных или недостаточных данных при быстрой регистрации
        возвращается HTTP 401
        '''
        with pytest.raises(falcon.HTTPUnauthorized):
            do_quick_auth(req, data)

    def test_signup(self, req, dbses):
        '''
        При вводе корректных данных, пользователь добавляется в БД и его
        идентификатор попадает в контекст запроса
        '''
        email = "hello@name.mail"
        data = {"email": email, "name": "Иван",
                "surname": "Иванов", "faculty_id": 1}
        do_quick_auth(req, data)

        user = dbses.query(User).filter_by(email = email).first()
        assert user is not None
        assert req.context['user']['uid'] == user.id


class TestOnPost:

    qa_mock = MagicMock()

    def test_auth_passthrough(self, auth_req):
        'Если пользователь уже аутентифицирован, то контекст не изменяется'
        quick_auth.auth_on_post(auth_req, None, None, None)
        assert auth_req.context['user'] == AUTHENTICATED_CONTEXT

    @patch('cyberdas.services.quick_auth._get_or_add_user', new = qa_mock)
    def test_quick_auth_called(self, dbses):
        'Аутентификация через POST должна использовать внутренний метод'
        data = {"email": "hello@name.mail", "name": "Иван",
                "surname": "Иванов", "faculty_id": 1}
        req = MockReq(dbses, json_data = data)
        quick_auth.auth_on_post(req, None, None, None)

        self.qa_mock.assert_called_once()

    def test_data_stripped(self, dbses):
        'Все данные, попадающие через POST, должны стрипаться'
        email = "hello@name.mail"
        data = {"email": email + '  ', "name": "  Иван",
                "surname": "Иванов  ", "faculty_id": 1}
        req = MockReq(dbses, json_data = data)
        quick_auth.auth_on_post(req, None, None, None)

        user = dbses.query(User).filter_by(email = email).first()
        assert user is not None
        assert user.name == "Иван"
        assert user.surname == "Иванов"


class TestOnToken:

    qa_mock = MagicMock()
    auth_on_token = quick_auth.auth_on_token('notify')

    def test_auth_passthrough(self, auth_req):
        'Если пользователь уже аутентифицирован, то контекст не изменяется'
        self.auth_on_token(auth_req, None, None, None)
        assert auth_req.context['user'] == AUTHENTICATED_CONTEXT

    def test_lacking_token(self, req):
        'При отсутствии токена в запросе возвращается HTTP 400'
        with pytest.raises(falcon.HTTPBadRequest):
            self.auth_on_token(req, None, None, None)

    def test_token_validation(self, dbses):
        'При невалидном токене возвращается HTTP 403'
        req = MockReq(dbses, token = 'blabla')
        with pytest.raises(falcon.HTTPForbidden):
            self.auth_on_token(req, None, None, None)

    @patch('cyberdas.services.quick_auth._get_or_add_user', new = qa_mock)
    def test_quick_auth_called(self, dbses):
        'Аутентификация через токен должна использовать внутренний метод'
        tok = Mail(cfg, 'notify').generate_token({"email": "hello@name.mail"})
        req = MockReq(dbses, token = tok)
        self.auth_on_token(req, None, None, None)

        self.qa_mock.assert_called_once()
