from os import environ
from datetime import datetime, timedelta

import falcon

from conftest import SES_LENGTH
from cyberdas.models import Session

environ['AUTH_UID'] = '1'


class TestRefresh:

    URI = '/refresh'

    def test_unauthorized(self, client):
        'При попытке продлить не залогинившись, возвращается 401 Unauthorized'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_401

    def test_post(self, oneUserDB, client, session):
        'Рефреш не отвечает на POST-запросы'
        print(datetime.now(), session)
        with oneUserDB.session as dbses:
            print(dbses.query(Session).all())
        resp = client.simulate_post(
            self.URI,
            cookies = {'SESSIONID': session['SESSIONID']},
            headers = {'XCSRF-Token': session['XCSRF-Token']}
        )
        print('finishing', datetime.now())
        assert resp.status == falcon.HTTP_405

    def test_get(self, client, session, oneUserDB):
        '''
        При отправке GET-запроса пользователь получает обратно свой cookie,
        срок действия которого продлен на длительность одной сессии с текущего
        момента времени; также, строка в БД с этой сессией тоже изменяется.
        '''
        with oneUserDB.session as dbses:
            ses_obj = dbses.query(Session).filter_by(uid = 1).first()
            old_expiration = ses_obj.expires.replace(tzinfo = None)

        now = datetime.now()
        resp = client.simulate_get(
            self.URI,
            cookies = {'SESSIONID': session['SESSIONID']}
        )

        assert resp.status == falcon.HTTP_200
        assert resp.cookies['SESSIONID'].max_age == SES_LENGTH

        with oneUserDB.session as dbses:
            ses_obj = dbses.query(Session).filter_by(uid = 1).first()
            new_expiration = ses_obj.expires.replace(tzinfo = None)
        assert new_expiration != old_expiration

        next_session_expires = (now + timedelta(seconds = SES_LENGTH))
        assert (new_expiration - next_session_expires).total_seconds() <= 0.01
