import pytest

from falcon import testing

from cyberdas.app import Service

pytest_plugins = ['utils.mockDB']


@pytest.fixture(scope = 'class')
def client():
    yield testing.TestClient(Service())
