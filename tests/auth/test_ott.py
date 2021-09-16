import falcon
from os import environ

from cyberdas.services.ott import validate_ott
from cyberdas.models import User


class TestResource:

    URI = '/account/ott'

    def test_requires_auth(self, client):
        'При отсутствии персональных данных в теле запроса возвращается ошибка'
        resp = client.simulate_post(self.URI, json = {'name': 'Иван'})
        assert resp.status == falcon.HTTP_401

    def test_registered_returns_token(self, defaultDB, client):
        'При вводе существующего в базе эмэйла возвращается токен с uid юзера'
        resp = client.simulate_post(
            self.URI,
            json = {'email': environ['REGISTERED_USER_EMAIL']}
        )
        assert resp.status == falcon.HTTP_201

        ans = resp.json
        assert 'token' in ans
        assert validate_ott(ans['token']) == {'uid': 1}

    def test_returns_token(self, client, dbses):
        '''
        При вводе данных незарегистрированного пользователя, он добавляется
        в БД и формируется токен с его новым uid
        '''
        email = 'hello@name.mail'
        data = {'email': email, 'name': 'Иван',
                'surname': 'Иванов', 'faculty_id': 1}
        resp = client.simulate_post(self.URI, json = data)
        assert resp.status == falcon.HTTP_201

        ans = resp.json
        assert 'token' in ans
        user = dbses.query(User).filter_by(email = email).first()
        assert validate_ott(ans['token']) == {'uid': user.id}
