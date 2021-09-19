import pytest
from unittest.mock import MagicMock

from cyberdas.services.personal_data_wall import required_personal_data
from cyberdas.exceptions import HTTPNotEnoughPersonalData


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

    def __init__(self, dbses, user = None):
        self.context = Context(dbses, user)


@pytest.fixture()
def req(dbses):
    yield MockReq(dbses, {'uid': 1})


class TestPDWall:

    def test_error(self, req):
        '''
        Если у пользователя не хватает данных для совершения запроса,
        то возвращается HTTP 442
        '''
        hook = required_personal_data(['course'])
        with pytest.raises(HTTPNotEnoughPersonalData):
            hook(req, None, None, None)

    @pytest.mark.parametrize('required_fields', [
        ['patronymic', 'course'],
        ['patronymic']
    ])
    def test_absent_fields(self, req, required_fields):
        '''
        Вместе с HTTP 442 должен возвращаться список полей (через запятую),
        которых не хватает для обработки запроса
        '''
        hook = required_personal_data(required_fields)
        exception_description = ','.join(required_fields)
        with pytest.raises(HTTPNotEnoughPersonalData) as e:
            hook(req, None, None, None)
        assert e.value.description == exception_description

    def test_enough_data(self, req):
        '''
        Если у пользователя хватает данных для совершения запроса,
        то ошибка не возникает
        '''
        hook = required_personal_data([])
        hook(req, None, None, None)

    def test_unexisting_field(self, req):
        '''
        Если по ошибке указано несуществующее в модели данных поле, то
        возвращается ошибка
        '''
        hook = required_personal_data(['bla'])
        with pytest.raises(AttributeError):
            hook(req, None, None, None)
