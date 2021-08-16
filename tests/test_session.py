import secrets
from os import environ
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy

from cyberdas.config import get_cfg
from cyberdas.models import Session as SessionModel
from cyberdas.services.session.session import Session as SessionController
from cyberdas.services.session.manager import SessionManager
from cyberdas.exceptions import BadAuthError, NoSessionError
cfg = get_cfg()


@pytest.fixture(scope = 'class')
def session():
    yield SessionController


class TestController:

    length = int(cfg['internal']['session.length'])

    def test_find(self, dbses, auth, session):
        'Метод find должен возвращать выражение для поиска этого объекта в БД'
        result = session.find(dbses, sid = environ['SESSIONID'])
        assert isinstance(result, sqlalchemy.orm.query.Query)

    def test_get(self, dbses, auth, session):
        'Метод get должен возвращать объект из БД, в случае его наличия в БД'
        result = session.get(dbses, sid = environ['SESSIONID'])
        assert result.sid == environ['SESSIONID']
        assert isinstance(result, SessionModel)

    def test_get_unexisting(self, dbses, session):
        'Метод get должен возвращать ошибку, в случае отсутствия объекта в БД'
        with pytest.raises(NoSessionError):
            session.get(dbses, sid = 'lkjwqasdaw')

    def test_new(self, dbses, session):
        'Метод new должен создавать новый объект в БД и устанавливать время его истечения' # noqa
        expires = session.new(
            dbses,
            ip = '123.123.123.123', uid = '1', user_agent = 'curl',
            sid = 'lol123', csrf_token = 'kek123'
        )
        now = datetime.now()

        ses = dbses.query(SessionModel).filter_by(sid = 'lol123').first()
        delta = ((now + timedelta(seconds = self.length)) - expires)
        assert delta.microseconds < 5 * 10**4
        assert ses is not None
        assert ses.csrf_token == 'kek123'
        assert ses.expires.replace(tzinfo = None) == expires

    def test_prolong(self, dbses, auth, session):
        'Метод prolong должен продлевать время жизни объекта в БД на еще один length' # noqa
        sid = environ['SESSIONID']
        ses = dbses.query(SessionModel).filter_by(sid = sid).first()
        old_expires = ses.expires

        expires = session.prolong(dbses, sid = sid)
        now = datetime.now()

        ses = dbses.query(SessionModel).filter_by(sid = sid).first()
        assert old_expires != ses.expires
        assert ses.expires.replace(tzinfo = None) == expires
        delta = ((now + timedelta(seconds = self.length)) - expires)
        assert delta.seconds < 1

    def test_prolong_unexisting(self, dbses, session):
        'Метод prolong должен возвращать ошибку, в случае отсутствия объекта в БД' # noqa
        with pytest.raises(NoSessionError):
            session.prolong(dbses, sid = 'lkjwqasdaw123asd')

    def test_terminate(self, dbses, auth, session):
        'Метод terminate должен удалять объект из БД'
        sid = environ['SESSIONID']
        session.terminate(dbses, sid = sid)
        ses = dbses.query(SessionModel).filter_by(sid = sid).first()
        assert ses is None

    def test_form_cookie(self, session):
        'Метод form_cookie должен формировать безопасный куки и ставить max_age'
        cookie_dict = session.form_cookie('lol123')
        assert cookie_dict['secure'] is True
        assert cookie_dict['http_only'] is True
        assert cookie_dict['same_site'] == 'Strict'
        assert cookie_dict['name'] == 'SESSIONID'
        assert cookie_dict['value'] == 'lol123'
        assert cookie_dict['max_age'] == self.length

    def test_form_cookie_max_age(self, session):
        'Метод form_cookie должен принимать аргумент для формирования max_age'
        cookie_dict = session.form_cookie('lol123', max_age = -1)
        assert cookie_dict['max_age'] == -1

    def test_extract_cookie(self, session):
        'Метод extract_cookie должен находить куки сессий из списка куки'
        cookie_dict = {'lol': 123}
        assert session.extract_cookie(cookie_dict) is None
        ses_cookie_dict = {'SESSIONID': 'abcw'}
        cookie_dict.update(ses_cookie_dict)
        assert session.extract_cookie(cookie_dict) == 'abcw'


@pytest.fixture(scope = 'class')
def manager():
    yield SessionManager()


class TestManager:

    secrets_mock = MagicMock()
    length = int(cfg['internal']['session.length'])

    @patch('secrets.token_urlsafe', new = secrets_mock)
    def test_tokens(self, dbses, manager):
        'Метод генерации токенов должен быть криптографически стойким'
        manager.gen_token()
        self.secrets_mock.assert_called()

    def test_start(self, dbses, manager):
        '''
        Метод start должен начинать новую сессию и возвращать словарь
        для формирования нового куки и CSRF-токен

        При этом он должен генерировать криптографически стойкий sid и
        csrf-токен (используя модуль secrets)
        '''
        cookie, csrf_token = manager.start(dbses, ip = '123.123.123.123',
                                           uid = '1', user_agent = 'curl')
        assert 'name' in cookie
        assert 'value' in cookie

        ses = dbses.query(SessionModel).filter_by(sid = cookie['value']).first()
        assert ses is not None
        assert ses.csrf_token == csrf_token

    def test_refresh(self, dbses, auth, manager):
        '''
        Метод refresh должен продлевать существующую сессию на еще одну
        максимальную продолжительность сессий и возвращать словарь для
        формирования куки с продленным сроком действия
        '''
        sid = environ['SESSIONID']
        ses = dbses.query(SessionModel).filter_by(sid = sid).first()
        old_expires = ses.expires

        cookie = manager.refresh(dbses, sid = sid)
        now = datetime.now()
        assert cookie['value'] == sid
        assert cookie['max_age'] == self.length

        ses = dbses.query(SessionModel).filter_by(sid = sid).first()
        assert old_expires != ses.expires
        delta = ((now + timedelta(seconds = self.length))
                 - ses.expires.replace(tzinfo = None))
        assert delta.seconds < 1

    def test_auth(self, dbses, auth, manager):
        '''
        Метод authenticate должен находить активную непросроченную сессию по
        куки и возвращать словарь с информацией о ней
        '''
        sid = environ['SESSIONID']
        data = manager.authenticate(dbses, {'SESSIONID': sid})
        assert data['uid'] == 1
        assert 'sid' in data
        assert 'csrf_token' in data

    def test_auth_no_cookie(self, dbses, manager):
        '''
        Метод authenticate должен возвращать ошибку при попытке
        аутентифицироваться без куки
        '''
        with pytest.raises(BadAuthError):
            manager.authenticate(dbses, {'what': 'is'})

    def test_auth_invalid_sid(self, dbses, manager):
        '''
        Метод authenticate должен возвращать ошибку при попытке
        аутентифицироваться по несуществующему sid'у
        '''
        with pytest.raises(BadAuthError):
            manager.authenticate(dbses, {'SESSIONID': secrets.token_urlsafe(32)}) # noqa

    def test_auth_expired(self, dbses, auth, manager):
        '''
        Метод authenticate должен возвращать ошибку при попытке
        аутентифицироваться по просроченной, но еще не удаленной из БД сессии
        '''
        sid = environ['SESSIONID']
        ses = dbses.query(SessionModel).filter_by(sid = sid)
        ses.update({SessionModel.expires: datetime.now() - timedelta(days = 1)})
        with pytest.raises(BadAuthError):
            manager.authenticate(dbses, {'SESSIONID': sid})

    def test_end(self, dbses, auth, manager):
        '''
        Метод end должен заканчивать существующую сессию и возвращать словарь
        для формирования куки с отрицательным сроком действия (это позволяет
        сбросить куки на стороне клиента)
        '''
        sid = environ['SESSIONID']
        cookie = manager.end(dbses, sid = sid)
        assert cookie['value'] == sid
        assert cookie['max_age'] == -1

        ses = dbses.query(SessionModel).filter_by(sid = sid).first()
        assert ses is None
