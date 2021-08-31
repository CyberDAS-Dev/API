import pytest
import json
from datetime import datetime, timedelta, date
from unittest.mock import MagicMock, patch

import falcon

from cyberdas.models import Queue, Slot


@pytest.fixture(scope = 'class')
def queueDB(defaultDB):
    '''
    База данных, содержащая две очереди со слотами
    '''
    living = Queue(
        name = 'living2021', title = 'Заселение 2021', duration = 5,
        description = 'Заселение 2021', waterfall = False,
        only_one_active = False, only_once = True
    )
    living_slots = [Slot(queue_name = 'living2021', id = x,
                    time = (datetime.now() + timedelta(minutes = x)))
                    for x in range(10)]

    music = Queue(
        name = 'music', title = 'Музкомната', duration = 5,
        description = 'Музкомната', waterfall = True,
        only_one_active = True, only_once = False
    )
    base = datetime.now() - timedelta(days = 1)
    datetime_range = [base + timedelta(days = x) for x in range(10)]
    music_slots = [Slot(queue_name = 'music', id = x, time = datetime_range[x])
                   for x in range(10)]

    defaultDB.setup_models([living, *living_slots, music, *music_slots])
    yield defaultDB


class TestCollection:

    URI = '/queues/music/slots'

    def test_post(self, a_client):
        'POST-запрос не поддерживается коллекцией'
        resp = a_client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_get(self, a_client, queueDB):
        'На GET-запрос без параметров возвращается список всех слотов'
        resp = a_client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_200
        assert len(json.loads(resp.text)) == 10

    def test_get_day(self, a_client, queueDB):
        'На GET-запрос с day в query возвращаются слоты на этот день'
        resp = a_client.simulate_get(self.URI, params = {'day': date.today()})
        assert resp.status == falcon.HTTP_200
        assert len(json.loads(resp.text)) == 1

    def test_get_offset(self, a_client, queueDB):
        'На GET-запрос с offset в query возвращается ошибка'
        resp = a_client.simulate_get(self.URI, params = {'offset': 3})
        assert resp.status == falcon.HTTP_400

    def test_get_day_offset(self, a_client, queueDB):
        'На GET-запрос с offset и day в query возвращается слайс слотов'
        resp = a_client.simulate_get(self.URI, params = {'day': date.today(),
                                                         'offset': 4})
        assert resp.status == falcon.HTTP_200
        assert len(json.loads(resp.text)) == 4

    @pytest.mark.parametrize("offset", [0, 1, 2, 89, 90, 91])
    def test_get_day_offset_limits(self, a_client, queueDB, offset):
        'Параметр offset должен принимать значения от 1 до 90'
        resp = a_client.simulate_get(self.URI, params = {'day': date.today(),
                                                         'offset': offset})
        if offset <= 90 and offset >= 1:
            assert resp.status == falcon.HTTP_200
        else:
            assert resp.status == falcon.HTTP_400

    def test_get_content(self, a_client, queueDB):
        'Содержимое в коллекции совпадает с содержимым по индивидуальному запросу' # noqa
        resp1 = a_client.simulate_get(self.URI)
        resp2 = a_client.simulate_get(self.URI.replace('/slots', '/slots/0'))
        assert json.loads(resp1.text)[0] == json.loads(resp2.text)

    def test_get_my(self, a_client, queueDB):
        'На запрос с my в query возвращаются только слоты этого пользователя'
        with queueDB.session as dbses:
            slots = dbses.query(Slot).filter_by(queue_name = 'music').all()
            slots[0].user_id = 1
            slots[5].user_id = 1

        resp = a_client.simulate_get(self.URI, params = {'my': 1})
        assert resp.status == falcon.HTTP_200
        content = json.loads(resp.text)
        assert len(content) == 2
        assert content[0]['id'] == 0
        assert content[1]['id'] == 5

        with queueDB.session as dbses:
            slots = dbses.query(Slot).filter_by(queue_name = 'music').all()
            slots[0].user_id = None
            slots[5].user_id = None

    def test_get_my_unauth(self, client, queueDB):
        '''
        На запрос с my в query от неаутентифицированного пользователя
        возвращается HTTP 401
        '''
        resp = client.simulate_get(self.URI, params = {'my': 1})
        assert resp.status == falcon.HTTP_401


class TestItem:

    URI = '/queues/music/slots/2'

    def test_post(self, a_client):
        'POST-запрос не поддерживается предметом'
        resp = a_client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_get_404(self, a_client, queueDB):
        'В случае отсутствия запрашиваемого слота возвращается 404 Not Found'
        resp = a_client.simulate_get(self.URI.replace('/2', '/40'))
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
        assert 'id' in valid_get
        assert 'time' in valid_get
        assert datetime.fromisoformat(valid_get['time'])  # время в isoformat'е
        assert 'free' in valid_get


@patch('cyberdas.services.mail.Mail.send', new = MagicMock())
class TestReserve:

    URI = '/queues/music/slots/2/reserve'

    def test_post_404(self, a_client, queueDB):
        'В случае отсутствия запрашиваемого слота возвращается 404 Not Found'
        resp = a_client.simulate_post(self.URI.replace('/2/', '/40/'))
        assert resp.status == falcon.HTTP_404

    def test_post(self, a_client, queueDB):
        'POST на свободный слот должен резервировать его под пользователя'
        resp = a_client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_201
        with queueDB.session as dbses:
            slot = dbses.query(Slot).filter_by(queue_name = 'music', id = 2).first() # noqa
            assert slot.user_id == 1

    def test_post_effect(self, a_client):
        'Успешный POST должен менять поле `free` у слота'
        resp = a_client.simulate_get(self.URI.replace('/reserve', ''))
        assert json.loads(resp.text)['free'] is False

    def test_post_twice(self, a_client):
        'При попытке забронировать занятый слот возвращается 403 Forbidden'
        resp = a_client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_403

    def test_post_old(self, a_client):
        'При попытке забронировать истёкший слот возвращается 403 Forbidden'
        resp = a_client.simulate_post(self.URI.replace('/2/', '/0/'))
        assert resp.status == falcon.HTTP_403

    def test_delete_404(self, a_client, queueDB):
        'В случае отсутствия запрашиваемого слота возвращается 404 Not Found'
        resp = a_client.simulate_delete(self.URI.replace('/2/', '/40/'))
        assert resp.status == falcon.HTTP_404

    def test_delete(self, a_client, queueDB):
        'DELETE от пользователя на его слот должен убирать бронирование слота'
        resp = a_client.simulate_delete(self.URI)
        assert resp.status == falcon.HTTP_204
        with queueDB.session as dbses:
            slot = dbses.query(Slot).filter_by(queue_name = 'music', id = 2).first() # noqa
            assert slot.user_id is None

    def test_delete_free(self, a_client, queueDB):
        'При попытке разбронировать свободный слот возвращается 404 Not Found'
        resp = a_client.simulate_delete(self.URI)
        assert resp.status == falcon.HTTP_404

    def test_delete_not_yours(self, a_client, queueDB):
        'При попытке разбронировать чужой слот возвращается 403 Forbidden'
        with queueDB.session as dbses:
            slot = dbses.query(Slot).filter_by(queue_name = 'music', id = 2).first() # noqa
            slot.user_id = 2
        resp = a_client.simulate_delete(self.URI)
        assert resp.status == falcon.HTTP_403

    def test_delete_old(self, a_client, queueDB):
        'Невозможно убрать своё бронирование уже прошедшего слота'
        with queueDB.session as dbses:
            slot = dbses.query(Slot).filter_by(queue_name = 'music', id = 0).first() # noqa
            slot.user_id = 1
        resp = a_client.simulate_delete(self.URI.replace('/2/', '/0/'))
        assert resp.status == falcon.HTTP_403

    def test_only_once(self, a_client, queueDB):
        'В очередь с флагом only_once можно занять только один слот'
        URI = self.URI.replace('music', 'living2021')
        resp = a_client.simulate_post(URI)
        assert resp.status == falcon.HTTP_201
        resp = a_client.simulate_post(URI.replace('/2/', '/3/'))
        assert resp.status == falcon.HTTP_403

        # Перебронирование
        a_client.simulate_delete(URI)
        resp = a_client.simulate_post(URI.replace('/2/', '/3/'))
        assert resp.status == falcon.HTTP_201

    def test_only_one_active(self, a_client, queueDB):
        '''
        В очередь с флагом only_one_active можно иметь только одну предстоящую
        запись
        '''
        resp = a_client.simulate_post(self.URI.replace('/2/', '/3/'))
        assert resp.status == falcon.HTTP_201
        resp = a_client.simulate_post(self.URI.replace('/2/', '/4/'))
        assert resp.status == falcon.HTTP_403

        with patch('cyberdas.resources.slots.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(days = 4) # noqa

            resp = a_client.simulate_post(self.URI.replace('/2/', '/8/'))
            assert resp.status == falcon.HTTP_201
