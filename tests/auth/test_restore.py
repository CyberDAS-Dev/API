from datetime import datetime, timedelta
import pytest
from os import environ

import falcon

from cyberdas.models import Session, LongSession

environ['AUTH_UID'] = '1'


class TestRestore:

    URI = '/restore'

    def test_empty_get(self, client):
        'Если в запросе отстствуют куки, возвращается 400 Bad Request'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_400

    @pytest.mark.parametrize("inv_cookie", [
        'lol', 'asadasdasdasd', 'lol:kek', 'hello@kitty', 'what?su12p'])
    def test_bad_get(self, client, inv_cookie):
        'Если куки невалидны, возвращается 400 Bad Request'
        resp = client.simulate_get(self.URI, cookies = {"REMEMBER": inv_cookie})
        assert resp.status == falcon.HTTP_400

    def test_get_active_session(self, client, long_session):
        '''
        При отправке запроса на создание новой сессии с помощью токена и наличию
        активной короткой сессии, связанной с этим токеном, возвращается
        400 Bad Request.
        '''
        resp = client.simulate_get(self.URI, cookies = long_session)
        assert resp.status == falcon.HTTP_400

    def test_get_expired(self, client, oneUserDB, long_only_session):
        with oneUserDB.session as dbses:
            ses = dbses.query(LongSession).filter_by(uid = 1).first()
            ses.expires = datetime.now() - timedelta(seconds = 10)
        resp = client.simulate_get(self.URI, cookies = long_only_session)
        assert resp.status == falcon.HTTP_400
        with oneUserDB.session as dbses:
            ses = dbses.query(LongSession).filter_by(uid = 1).first()
            ses.expires = datetime.now() + timedelta(hours = 100)

    @pytest.fixture(scope = 'class')
    def valid_get(self, client, long_only_session):
        resp = client.simulate_get(self.URI, cookies = long_only_session)
        yield resp

    def test_get(self, valid_get):
        '''
        При отправке токена и отсутствию короткой сессии возвращается 200 OK и
        новая пара токенов
        '''
        assert valid_get.status == falcon.HTTP_200

    def test_long_token(self, valid_get, long_only_session, oneUserDB):
        '''
        Проверка корректности формирования нового токена:
        - он должен отличаться от старого валидатором, но не селектором
        - старый токен должен пропасть из БД
        - новый токен должен быть в БД
        - у нового токена должна быть ассоциированная сессия
        '''
        old_c = long_only_session['REMEMBER'].split(':')
        new_c = valid_get.cookies['REMEMBER'].value.split(':')
        assert old_c[1] != new_c[1]
        assert old_c[0] == new_c[0]
        with oneUserDB.session as dbses:
            old_s = dbses.query(LongSession).filter_by(validator = old_c[1]).first() # noqa
            new_s = dbses.query(LongSession).filter_by(validator = new_c[1]).first() # noqa
            assert old_s is None
            assert new_s is not None
            assert new_s.associated_sid is not None

    def test_session(self, valid_get, oneUserDB):
        '''
        Проверка корректности формирования сессионого токена:
        - он должен быть в БД
        - он должен иметь ровно один ассоциированный токен
        - этот ассоциированный токен тоже должен быть эту сессию ассоциированной
        '''
        new_c = valid_get.cookies['SESSIONID'].value
        long = valid_get.cookies['REMEMBER'].value.split(':')
        with oneUserDB.session as dbses:
            new_s = dbses.query(Session).filter_by(sid = new_c).first()
            assert new_s is not None
            assert len(new_s.associated) == 1
            assert new_s.associated[0].validator == long[1]

    def test_security_error(self, client, valid_get, long_only_session):
        '''
        Проверка работы anti-theft фичи. Токен, полученный в valid_get,
        из той же серии, что и long_cookie_only. Но токен из valid_get более
        свежий.

        Anti-theft работает так: если кто-то предъявит невалидный токен, но из
        валидной серии, то это означает то, что этот невалидный токен был
        украден - или, что валидный токен украл и уже использовал злоумышленик.
        Поэтому нужно прерывать все сессии пользователя.

        Валдиной серией называется та, чей selector присутствует в базе данных.
        '''
        resp = client.simulate_get(self.URI, cookies = long_only_session)
        assert resp.status == falcon.HTTP_400
