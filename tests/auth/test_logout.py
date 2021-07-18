from os import environ

import falcon

from cyberdas.models import Session, LongSession

environ['AUTH_UID'] = '1'


class TestLogout:

    URI = '/logout'

    def test_unauthorized(self, client):
        'При попытке выйти не залогинившись, возвращается 401 Unauthorized'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_401

    def test_post(self, client, authorize):
        'Логаут не отвечает на POST-запросы'
        resp = client.simulate_post(
            self.URI,
            cookies = {'SESSIONID': authorize['SESSIONID']},
            headers = {'XCSRF-Token': authorize['XCSRF-Token']}
        )
        assert resp.status == falcon.HTTP_405

    def test_get(self, client, authorize):
        '''
        При отправке GET-запроса пользователь получает обратно свой cookie, но
        просрочившийся в прошлом
        '''
        resp = client.simulate_get(
            self.URI,
            cookies = {'SESSIONID': authorize['SESSIONID']}
        )
        assert resp.status == falcon.HTTP_200
        assert resp.cookies['SESSIONID'].max_age == -1

    def test_clean_db(self, oneUserDB):
        'При логауте сессия должна удаляться из БД'
        with oneUserDB.session as dbses:
            session = dbses.query(Session).filter_by(uid = 1).first()
            assert session is None


class TestLogoutAssociated:

    URI = TestLogout.URI

    def test_associated(self, oneUserDB, client, long_authorize):
        'Проверка того, что ассоциированая долгая сессия тоже удаляется'
        resp = client.simulate_get(self.URI, cookies = long_authorize)
        assert resp.status == falcon.HTTP_200
        assert len(resp.cookies) == 2
        assert 'REMEMBER' in resp.cookies and 'SESSIONID' in resp.cookies
        with oneUserDB.session as dbses:
            long_session = dbses.query(LongSession).filter_by(uid = 1).first()
            assert long_session is None
            session = dbses.query(Session).filter_by(uid = 1).first()
            assert session is None
