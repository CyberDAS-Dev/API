import pytest
from time import sleep
from unittest.mock import MagicMock, patch

import falcon

from cyberdas.services.ott import generate_ott, validate_ott, support_ott


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

    def __init__(self, dbses, user = None, headers = None):
        self.context = Context(dbses, user)
        self.headers = headers

    def get_header(self, name, *args, **kwargs):
        return self.headers[name]

    @property
    def uri(self):
        return '/queues/123'


class TestGeneration:

    data = {'lol': 1, '2': 4}

    def test_generation(self):
        'Данные должны обратимо оборачиваться в токены'
        tok = generate_ott(self.data)
        assert tok != self.data
        deciph = validate_ott(tok)
        assert deciph == self.data

    def test_validation(self):
        'Если токен некорректный, возвращается False'
        deciph = validate_ott("lol123asd")
        assert deciph is False

    @patch('cyberdas.services.ott.max_age', new = 0)
    def test_max_age(self):
        'Токен истекает через некоторое время'
        tok = generate_ott(self.data)
        sleep(1)
        deciph = validate_ott(tok)
        assert deciph is False


class TestHook:

    user_context = {'uid': 2}
    tokenized_context = generate_ott(user_context)

    def test_already_authorised(self):
        'Хук не изменяет контекст уже аутентифицированного пользователя'
        req = MockReq(MagicMock(), self.user_context)
        support_ott(req, None, None, None)
        assert req.context.user == self.user_context

    @pytest.mark.parametrize('auth_header', [
        f'Bearer {tokenized_context} blabla',
        f'Token {tokenized_context}',
        'Bearer baddata',
    ])
    def test_bad_header(self, auth_header):
        'Если заголовок не соответствует требованиям, возвращается HTTP 401'
        req = MockReq(MagicMock(), headers = {'Authorization': auth_header})
        with pytest.raises(falcon.HTTPUnauthorized):
            support_ott(req, None, None, None)

    def test_context_modified(self):
        'Если заголовок корректный, то данные из токена добавляются в контекст'
        req = MockReq(
            MagicMock(),
            headers = {'Authorization': f'Bearer {self.tokenized_context}'}
        )
        support_ott(req, None, None, None)
        assert req.context.user == self.user_context
