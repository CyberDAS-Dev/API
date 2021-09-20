import pytest
from datetime import datetime, timedelta

import falcon

from cyberdas.models import Maintenance, User
from cyberdas.services.ott import generate_ott


@pytest.fixture(scope = 'class')
def maintenanceDB(defaultDB):
    '''
    База данных, содержащая две заявки на технические услуги
    '''
    base = datetime.now() - timedelta(days = 1)
    datetime_range = [base + timedelta(days = x) for x in range(10)]

    req1 = Maintenance(
        category = 'plumber', building = 2, room = 1131,
        text = 'bla', user_id = 1, created_at = datetime_range[0]
    )

    req2 = Maintenance(
        category = 'electrician', building = 1, room = 523,
        text = 'lol', user_id = 2, created_at = datetime_range[2]
    )

    with defaultDB.session as dbses:
        user = dbses.query(User).filter_by(id = 1).first()
        user.building = 1
        user.room = 1121
        dbses.flush()

    defaultDB.setup_models([req1, req2])
    yield defaultDB

    with defaultDB.session as dbses:
        user = dbses.query(User).filter_by(id = 1).first()
        user.building = None
        user.room = None
        dbses.flush()


class TestFeedbackCollection:

    URI = '/maintenance'
    default_data = {'category': 'plumber', 'text': '1'}

    @pytest.mark.parametrize('data', [
        {'category': 'plumber'},
        {'text': 'blabla'},
        {'category': 'жалоба', 'text': 'blabla'},
    ])
    def test_post_schema(self, a_client, data):
        'Запрос с недостаточными или некорректными данными возвращает HTTP 400'
        resp = a_client.simulate_post(self.URI, json = data)
        assert resp.status == falcon.HTTP_400

    def test_post(self, a_client, maintenanceDB, dbses):
        'POST создаёт новый заявку'
        text, category = 'bla? bla!', 'plumber'
        data = {'text': text, 'category': category}
        resp = a_client.simulate_post(self.URI, json = data)
        assert resp.status == falcon.HTTP_201

        item = dbses.query(Maintenance).filter_by(user_id = 1).all()[-1]
        assert item is not None
        assert item.text == text
        assert item.category == category

        # Корпус и комната подтягиваются из данных пользователя
        assert item.building == 1
        assert item.room == 1121

    def test_auth_is_required(self, client):
        'Для создания заявки необходима аутентифиакция'
        resp = client.simulate_post(self.URI, json = self.default_data)
        assert resp.status == falcon.HTTP_401

    def test_ott_supported(self, client, maintenanceDB):
        'Поддерживается OTT аутентификация'
        t = generate_ott({'uid': 1})
        resp = client.simulate_post(self.URI, json = self.default_data,
                                    headers = {'Authorization': f'Bearer {t}'})
        assert resp.status == falcon.HTTP_201

    def test_room_required(self, a_client, dbses):
        'Для успешного запроса требуется комната и корпус в персональных данных'
        user = dbses.query(User).filter_by(id = 1).first()
        user.building = None
        user.room = None
        dbses.commit()

        resp = a_client.simulate_post(self.URI, json = self.default_data)
        assert resp.status_code == 442
        assert resp.json['description'] == 'building,room'
