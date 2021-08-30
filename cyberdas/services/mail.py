import re
import smtplib
import ssl

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer, BadData


class Mail(object):
    '''
    Базовой класс, предоставляющий сервис почты и токенов.
    '''

    def __init__(self, cfg, sender):
        self.smtp_server = cfg['mail']['server']
        self.smtp_port = int(cfg['mail']['port'])
        self.account_login = cfg['mail'][f'{sender}.login']
        self.account_password = cfg['mail'][f'{sender}.password']
        self.sent_from = cfg['mail'][f'{sender}.name']
        self.mail_key = cfg['security'][f'secret.{sender}']
        self.mail_salt = cfg['security'][f'salt.{sender}']
        self.mail_expiry = cfg['mail'].get(f'{sender}.expiry', None)
        if self.mail_expiry is not None:
            self.mail_expiry = int(self.mail_expiry)

    def send(self, to, subject, content, log):
        '''
        Отправляет письмо на указанный адрес.

        Аргументы:
            to(str, необходимо): эмэйл-адрес получателя

            subject(str, необходимо): тема письма

            content(dict, необходимо): словарь, содержащий текстовую и HTML
                версию письма, при этом они могут являться списками из контента.

            log(необходимо): логгер, позволяющий выводить сообщения об ошибках.
        '''
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sent_from
        msg['To'] = to
        plain = MIMEText(content['plain'], 'plain')
        html = MIMEText(content['html'], 'html')
        msg.attach(plain)
        msg.attach(html)
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.ehlo()
            server.starttls(context = context)
            server.ehlo()
            server.login(self.account_login, self.account_password)
            server.sendmail(self.sent_from, to, msg.as_string())
            server.close()
        except Exception as e:
            log.error(e)
            raise e

    def validate_address(self, email):
        '''
        Проверяет, является ли аргумент email эмэйлом, используя примитивное
        регулярное выражение.
        '''
        if re.match(r"^\S+@\S+$", email) is None:
            return False
        return True

    def generate_token(self, data):
        '''
        Возвращает цифровую сигнатуру письма, содержащую подписанные данные.
        Сохраняет структуру питоновских данных при расшифровке.

        Аргументы:
            data(str | list | dict, необходимо): строка или словарь, которую
                необходимо подписать.
        '''
        serializer = URLSafeTimedSerializer(self.mail_key)
        return serializer.dumps(data, salt = self.mail_salt)

    def confirm_token(self, token, expires = False):
        '''
        Проверяет цифровую сигнатуру письма.
        Возвращает подписанные данные или False, если подпись невалидна.
        Сохраняет структуру питоновских данных.

        Аргументы:
            token(str, необходимо): строка, содержащая сигнатуру, которую
                необходимо проверить.

            expires(bool, опционально): флаг, устанавливающий, может ли токен
                в письме истечь.
        '''
        serializer = URLSafeTimedSerializer(self.mail_key)
        args = {'salt': self.mail_salt}
        if expires:
            args.update({'max_age': self.mail_expiry})

        try:
            data = serializer.loads(token, **args)
        except BadData:
            return False
        return data
