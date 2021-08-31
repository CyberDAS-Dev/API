import os
import re
import base64
from smtplib import SMTPNotSupportedError
from time import sleep
import pytest
from unittest.mock import MagicMock

from itsdangerous import URLSafeTimedSerializer

from cyberdas.services.mail import Mail, TransactionMail
from cyberdas.config import get_cfg

HOSTNAME = '127.0.0.1'
PORT = 8025
LOGIN = 'lol'
PASSWORD = 'kek'
SENDER = 'signup'

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
    cfg.set('mail', f'{SENDER}.login', LOGIN)
    cfg.set('mail', f'{SENDER}.password', PASSWORD)
    cfg.set('mail', f'{SENDER}.expiry', '0')
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
        yield Mail(mock_smtp_cfg, SENDER)

    @pytest.fixture(scope = 'class')
    def token(self, mail):
        yield mail.generate_token(self.to)

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

    def test_token_deciphered(self, mail, token):
        'Проверка расшифровки токена'
        deciphered = mail.confirm_token(token)
        assert deciphered is not None
        assert deciphered == self.to

    def test_token_expiry(self, mail, token):
        'Проверка возможности просрочить токен'
        sleep(1)
        # да, ставить слипы в тесты - очень плохо, но токен должен
        # просуществовать минимум секунду что бы просрочиться
        deciphered = mail.confirm_token(token, expires = True)
        assert deciphered is False

    def test_token_bad(self, mail):
        'Проверка поведения функции расшифровки токена при плохом вводе'
        assert mail.confirm_token('blablabla') is False

    def test_token_gen(self, mail):
        'Проверка интерфейса генерации токенов'
        # словари
        token = mail.generate_token({'email': self.to})
        assert mail.confirm_token(token)['email'] == self.to
        # списки
        token = mail.generate_token([self.to, self.subject])
        assert len(mail.confirm_token(token)) == 2

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
        mail.send(self.to, self.subject, self.content, MagicMock(),
                  files = ['./LICENSE'])
        yield smtpd_tls.messages

    def test_email_sent(self, messages):
        'Проверяет, что письмо было послано и дошло'
        assert len(messages) == 1

    def test_email_ssl(self, mail, smtpd):
        'Проверяет, что без SSL письма не отправляются'
        with pytest.raises(SMTPNotSupportedError):
            mail.send(self.to, self.subject, self.content, MagicMock())
        assert len(smtpd.messages) == 0


class TestTransactionMail:

    email = 'lol@das.net'
    prefix = 'api.cyberdas.net/'
    frontend = 'https://cyberdas.net'
    next = 'verify'
    backend_next = 'signup/validate'
    fake_transaction = 'lol/kek'

    @pytest.fixture(scope = 'class')
    def mail(self, mock_smtp_cfg):
        yield TransactionMail(
            mock_smtp_cfg, SENDER, 'Transaction for you!', 'signup',
            self.frontend, self.backend_next, False
        )

    def extract_url(self, letter, isFront = False, fake_trans = False):
        'Извлекает токен из верификационного письма'
        payload = letter.get_payload()[0].get_payload()
        payload = base64.b64decode(payload.encode('utf-8')).decode('utf-8')
        if isFront:
            location = f'{self.frontend}/{self.next}'
        elif fake_trans:
            location = f'{self.prefix}/{self.fake_transaction}'
        else:
            location = f'{self.prefix}/{self.backend_next}'
        url = re.findall(rf'{location}\?[\w\=\.\-\_\&\/]+', payload)[0]
        return url

    def extract_token(self, letter, isFront = False):
        'Извлекает токен из верификационного письма'
        token = self.extract_url(letter, isFront).split('=')[1].split('&')[0]
        return token

    @pytest.fixture
    def messages(self, mail, smtpd_tls):
        'Возвращает сообщения, посланные модулем'
        req = MockReq(self.prefix)
        mail.send(req, self.email, {'email': self.email})
        yield smtpd_tls.messages

    @pytest.fixture
    def messages_next(self, mail, smtpd_tls):
        'Возвращает сообщения, посланные модулем (с переадресацией `next`)'
        req = MockReq(self.prefix, self.next)
        mail.send(req, self.email, {'email': self.email})
        yield smtpd_tls.messages

    @pytest.fixture
    def messages_trans(self, mail, smtpd_tls):
        'Возвращает сообщения, посланные модулем с переписанным урлом транзакции' # noqa
        req = MockReq(self.prefix)
        mail.send(req, self.email, {'email': self.email},
                  transaction_url = self.fake_transaction)
        yield smtpd_tls.messages

    def test_email_sent(self, messages):
        'Проверяет, что письмо было послано и дошло'
        assert len(messages) == 1

    def test_email_sent_next(self, messages_next):
        'Проверяет, что письмо было послано и дошло (с переадресацией `next`)'
        assert len(messages_next) == 1

    def test_email_contains_token(self, messages):
        'Проверяет наличие токена в письме'
        token = self.extract_token(messages[0])
        assert token is not False

    def test_email_contains_token_next(self, messages_next):
        'Проверяет наличие токена в письме (с переадресацией `next`)'
        token = self.extract_token(messages_next[0], True)
        assert token is not False

    def test_email_contains_backend_ref_next(self, messages_next):
        'Проверяет наличие ссылки на бэкенд в письме (с переадресацией `next`)'
        url = self.extract_url(messages_next[0], True)
        assert f'backend={self.prefix}/{self.backend_next}' in url

    def test_email_token_validity(self, mail, messages):
        'Проверяет валидность токена в письме'
        token = self.extract_token(messages[0])
        assert mail.confirm_token(token) is not False

    def test_email_token_validity_next(self, mail, messages_next):
        'Проверяет валидность токена в письме (с переадресацией `next`)'
        token = self.extract_token(messages_next[0], True)
        print(token)
        assert mail.confirm_token(token) is not False

    def test_email_transaction_is_rewriteable(self, mail, messages_trans):
        'Проверяет возможность переписать транзакционный URL для одного письма'
        url = self.extract_url(messages_trans[0], fake_trans = True)
        assert f'{self.prefix}/{self.fake_transaction}' in url
