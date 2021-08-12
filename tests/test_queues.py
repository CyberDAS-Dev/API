import pytest
import json
from datetime import datetime, timedelta

import falcon

from cyberdas.models import Queue, Slot


@pytest.fixture(scope = 'class')
def queueDB(defaultDB):
    '''
    База данных, содержащая две очереди со слотами
    '''
    living = Queue(
        name = 'living2021', title = 'Заселение 2021', duration = 5,
        description = 'Заселение 2021', waterfall = False, only_once = True
    )
    living_slots = [Slot(queue_name = 'living2021', id = x,
                    time = datetime.now()) for x in range(10)]

    music = Queue(
        name = 'music', title = 'Музкомната', duration = 5,
        description = 'Музкомната', waterfall = True, only_once = False
    )
    base = datetime.now() - timedelta(days = 1)
    datetime_range = [base + timedelta(days = x) for x in range(10)]
    music_slots = [Slot(queue_name = 'music', id = x, time = datetime_range[x])
                   for x in range(10)]

    defaultDB.setup_models([living, *living_slots, music, *music_slots])
    yield defaultDB


class TestCollection:

    URI = '/queues'

    def test_get(self, a_client, queueDB):
        'На GET-запрос возвращается 200 OK со всеми очередями'
        resp = a_client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_200
        assert len(json.loads(resp.text)) == 2

    def test_post(self, a_client):
        'POST-запрос не поддерживается коллекцией'
        resp = a_client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_get_content(self, a_client, queueDB):
        'Содержимое в коллекции совпадает с содержимым по индивидуальному запросу' # noqa
        resp1 = a_client.simulate_get(self.URI)
        resp2 = a_client.simulate_get(self.URI.replace('/queues', '/queues/living2021')) # noqa
        assert json.loads(resp1.text)[0] == json.loads(resp2.text)


class TestItem:

    URI = '/queues/living2021'

    def test_post(self, a_client):
        'POST-запрос не поддерживается предметом'
        resp = a_client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_get_404(self, a_client, queueDB):
        'В случае отсутствия запрашиваемой очереди возвращается 404 Not Found'
        resp = a_client.simulate_get(self.URI.replace('living2021', 'onetwo'))
        assert resp.status == falcon.HTTP_404

    def test_get(self, a_client, queueDB):
        'На GET-запрос возвращается 200 OK'
        resp = a_client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_200

    @pytest.fixture(scope = 'class')
    def valid_get(self, a_client, queueDB):
        resp = a_client.simulate_get(self.URI)
        yield json.loads(resp.text)

    def test_get_content(self, valid_get):
        assert 'name' in valid_get
        assert 'title' in valid_get
        assert 'description' in valid_get
        assert 'duration' in valid_get
        assert 'waterfall' in valid_get
        assert 'only_once' in valid_get
