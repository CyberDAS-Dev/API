import re
import smtplib
import ssl

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer, BadData


class Mail(object):
    '''
    Базовой класс, предоставляющий почтовый сервис.
    '''

    def __init__(self, cfg):
        self.mail_key = cfg['security']['secret.signup']
        self.mail_salt = cfg['security']['salt.signup']
        self.mail_expiry = int(cfg['mail']['expiry'])
        self.smtp_server = cfg['mail']['server']
        self.smtp_port = int(cfg['mail']['port'])
        self.account_login = cfg['mail']['login']
        self.account_password = cfg['mail']['password']
        self.sent_from = cfg['mail']['name']

    def send(self, to, subject, content, log):
        '''
        Отправляет письмо на указанный адрес.

        Аргументы:
            to(str, необходимо): эмэйл-адрес получателя

            subject(str, необходимо): тема письма

            content(list, необходимо): список из содержимого письма. Может
                включать в себя текст, HTML или изображения.

            log(необходимо): логгер, позволяющий выводить сообщения об ошибках.
        '''
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sent_from
        msg['To'] = to
        data = MIMEText(content, 'html')  # мы отправляем только HTML
        msg.attach(data)
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
        Возвращает цифровую сигнатуру письма, содержащую адрес получателя

        Аргументы:
            data(str, необходимо): строка, которую необходимо подписать
        '''
        serializer = URLSafeTimedSerializer(self.mail_key)
        return serializer.dumps(data, salt = self.mail_salt)

    def confirm_token(self, token):
        '''
        Проверяет цифровую сигнатуру письма.
        Возвращает подписанные данные или False, если подпись невалидна.

        Аргументы:
            token(str, необходимо): строка, содержащая сигнатуру, которую
                необходимо проверить
        '''
        serializer = URLSafeTimedSerializer(self.mail_key)
        try:
            data = serializer.loads(
                token,
                salt = self.mail_salt,
                max_age = self.mail_expiry
            )
        except BadData:
            return False
        return data
