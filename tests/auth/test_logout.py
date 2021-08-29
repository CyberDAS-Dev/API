import falcon

from cyberdas.models import Session


class TestLogout:

    URI = '/account/logout'

    def test_unauthorized(self, client):
        'При попытке выйти не залогинившись, возвращается 401 Unauthorized'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_401

    def test_post(self, client, auth):
        'Логаут не отвечает на POST-запросы'
        resp = client.simulate_post(
            self.URI,
            cookies = {'SESSIONID': auth['SESSIONID']},
            headers = {'X-CSRF-Token': auth['X-CSRF-Token']}
        )
        assert resp.status == falcon.HTTP_405

    def test_get(self, client, auth):
        '''
        При отправке GET-запроса пользователь получает обратно свой cookie, но
        просрочившийся в прошлом
        '''
        resp = client.simulate_get(
            self.URI,
            cookies = {'SESSIONID': auth['SESSIONID']}
        )
        assert resp.status == falcon.HTTP_204
        assert resp.cookies['SESSIONID'].max_age == -1

    def test_clean_db(self, dbses):
        'При логауте сессия должна удаляться из БД'
        session = dbses.query(Session).filter_by(uid = 1).first()
        assert session is None
