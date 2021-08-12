import os
import re
import base64
import pytest
from unittest.mock import MagicMock

from itsdangerous import URLSafeTimedSerializer

from cyberdas.services import Mail, SignupMail
from cyberdas.config import get_cfg

HOSTNAME = '127.0.0.1'
PORT = 8025
LOGIN = 'lol'
PASSWORD = 'kek'

# Эти настройки нужны для модуля smtpdfix, предоставляющего fixture - smtpd
os.environ['SMTPD_HOST'] = HOSTNAME
os.environ['SMTPD_PORT'] = str(PORT)
os.environ['SMTPD_LOGIN_NAME'] = LOGIN
os.environ['SMTPD_LOGIN_PASSWORD'] = PASSWORD


@pytest.fixture(scope = 'class')
def mock_smtp_cfg():
    'Подмена почтового сервера на тестировочный'
    cfg = get_cfg()
    cfg.set('mail', 'server', HOSTNAME)
    cfg.set('mail', 'port', str(PORT))
    cfg.set('mail', 'login', LOGIN)
    cfg.set('mail', 'password', PASSWORD)
    yield cfg


@pytest.fixture
def smtpd_tls(smtpd):
    'smtpd с включенным TLS'
    smtpd.config.use_starttls = True
    yield smtpd


class MockReq:

    def __init__(self, prefix, next = None):
        self.forwarded_prefix = prefix
        self.next = next
        self.context = MagicMock()
        self.context.logger.error = print

    def get_param(self, string):
        if string == 'next':
            return self.next


class TestMail:

    to = 'user@das.net'
    subject = 'hello'
    content = {'html': 'not much', 'plain': 'not much'}

    @pytest.fixture(scope = 'class')
    def mail(self, mock_smtp_cfg):
        yield Mail(mock_smtp_cfg)

    def test_token(self, mail):
        'Проверка алгоритма генерации токена с помощью его дешифровки'
        token = mail.generate_token(self.to)
        key = mail.mail_key
        salt = mail.mail_salt
        expiry = mail.mail_expiry
        serializer = URLSafeTimedSerializer(key)
        deciphered = serializer.loads(token, salt = salt, max_age = expiry)
        assert deciphered is not None
        assert deciphered == self.to

    def test_bad_token(self, mail):
        'Проверка поведения функции расшифровки токена при плохом вводе'
        assert mail.confirm_token('blablabla') is False

    @pytest.mark.parametrize("input_addr", [
        'hello@lol.ru', 'ivan@ivanovi.com', 'where@com', 'hello123@site.net'
    ])
    def test_addr_valid(self, mail, input_addr):
        'Проверяет валидацию адреса (корректные адреса)'
        assert mail.validate_address(input_addr) is True

    @pytest.mark.parametrize("input_addr", [
        'lol', 'asd12easdzxc', 'lol.com', 'lol.asd', 'lwxz!#dsa'
    ])
    def test_addr_invalid(self, mail, input_addr):
        'Проверяет валидацию адреса (некорректные адреса)'
        assert mail.validate_address(input_addr) is False

    @pytest.fixture
    def messages(self, mail, smtpd_tls):
        'Возвращает сообщения, посланные модулем'
        mail.send(self.to, self.subject, self.content, MagicMock())
        yield smtpd_tls.messages

    def test_email_sent(self, messages):
        'Проверяет, что письмо было послано и дошло'
        assert len(messages) == 1

    def test_email_ssl(self, mail, smtpd):
        'Проверяет, что без SSL письма не отправляются'
        mail.send(self.to, self.subject, self.content, MagicMock())
        assert len(smtpd.messages) == 0


class TestSignupMail:

    email = 'lol@das.net'
    prefix = 'api.cyberdas.net/'
    next = 'cyberdas.net/verify'

    @pytest.fixture(scope = 'class')
    def mail(self, mock_smtp_cfg):
        yield SignupMail(mock_smtp_cfg)

    def test_token_gen(self, mail):
        'Проверка интерфейса генерации токенов'
        token = mail.generate_token(self.email)
        assert mail.confirm_token(token)['email'] == self.email

    def test_token_redirect_gen(self, mail):
        'Проверка интерфейса генерации токенов для писем с переадрессацией'
        token = mail.generate_token(self.email, self.next)
        data = mail.confirm_token(token)
        assert data['email'] == self.email
        assert data['redirect'] == self.next

    def test_bad_token(self, mail):
        'Проверка поведения функции расшифровки токена при плохом вводе'
        assert mail.confirm_token('blablabla') is False

    def extract_token(self, letter):
        'Извлекает токен из верификационного письма'
        payload = letter.get_payload()[0].get_payload()
        payload = base64.b64decode(payload.encode('utf-8')).decode('utf-8')
        token = re.findall(r'/verify\?[\w\=\.\-\_]+', payload)[0]
        token = token.split('=')[1]
        return token

    @pytest.fixture
    def messages(self, mail, smtpd_tls):
        'Возвращает сообщения, посланные модулем'
        req = MockReq(self.prefix, self.next)
        mail.send_verification(req, self.email)
        yield smtpd_tls.messages

    def test_email_sent(self, messages):
        'Проверяет, что письмо было послано и дошло'
        assert len(messages) == 1

    def test_email_contains_token(self, messages):
        'Проверяет наличие токена в письме'
        token = self.extract_token(messages[0])
        assert token is not False

    def test_email_token_validity(self, mail, messages):
        'Проверяет валидность токена в письме'
        token = self.extract_token(messages[0])
        assert mail.confirm_token(token) is not False
