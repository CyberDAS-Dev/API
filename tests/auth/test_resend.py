from unittest.mock import ANY, MagicMock, patch

import falcon

from conftest import REGISTERED_USER_EMAIL


class TestResend:

    URI = '/resend'
    smtp_mock = MagicMock()

    def test_get(self, client):
        'Эндпоинт повторной отправки писем не отвечает на GET-запросы'
        resp = client.simulate_get(self.URI)
        assert resp.status == falcon.HTTP_405

    def test_no_data(self, client):
        'Если пользователь не отправил достаточно данных, возвращается HTTP 400'
        resp = client.simulate_post(self.URI)
        assert resp.status == falcon.HTTP_400

    def test_bad_email(self, client):
        '''
        Если пользователь указал некорректный или уже верифицированный эмэйл,
        возвращается HTTP 200, с формулировкой 'если такой пользователь найден,
        то письмо отправлено'
        '''
        resp = client.simulate_post(self.URI, json = {"email": "lol@das.net"})
        assert resp.status == falcon.HTTP_200

    @patch('cyberdas.services.SignupMail.send_verification', new = smtp_mock)
    def test_post(self, client, oneUserDB):
        'Если пользователь указал верный эмэйл, ему придет письмо с токеном'
        resp = client.simulate_post(self.URI,
                                    json = {"email": REGISTERED_USER_EMAIL})
        assert resp.status == falcon.HTTP_200
        self.smtp_mock.assert_called_once_with(ANY, REGISTERED_USER_EMAIL)
