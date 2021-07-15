import re
import smtplib
import ssl
from os import path

import jinja2

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
        Возвращает цифровую сигнатуру письма, содержащую подписанные данные.

        Аргументы:
            data(str, необходимо): строка, которую необходимо подписать.
        '''
        serializer = URLSafeTimedSerializer(self.mail_key)
        return serializer.dumps(data, salt = self.mail_salt)

    def confirm_token(self, token):
        '''
        Проверяет цифровую сигнатуру письма.
        Возвращает подписанные данные или False, если подпись невалидна.

        Аргументы:
            token(str, необходимо): строка, содержащая сигнатуру, которую
                необходимо проверить.
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


class SignupMail(Mail):

    def __init__(self, cfg):
        super().__init__(cfg)
        self.sep = ';'  # символ, не встречающийся в email'ах и url'ах - используется как разделитель # noqa

    def send_verification(self, req, email):
        '''
        Отправляет верификационное письмо на указанный ящик и возвращает адресс,
        указанный в письме.

        Аргументы:
            req(необходим): входящий запрос, из него извлекаются параметры
                для переадресации.

            email(string, необходим): адрес почты, на которую нужно отправить
                письмо.
        '''
        mail_token = self.generate_token(email, req.get_param('next'))
        verify_url = f'{req.forwarded_prefix}/verify?token={mail_token}'
        template = self.load_template('verify_email')
        rendered_template = template.render(verify_url = verify_url)

        self.send(
            to = email,
            subject = 'Подтверждение e-mail адреса в CyberDAS',
            content = rendered_template,
            log = req.context.logger
        )
        return verify_url

    def generate_token(self, email, redirect = None):
        '''
        Возвращает цифровую сигнатуру письма, содержащую адрес получателя и
        ссылку на страницу, на которую он должен попасть после подтверждения.

        Аргументы:
            email(str, необходимо): эмэйл-адрес, требующий подтверждения.

            redirect(str, опционально): ссылка на страницу, на которую нужно
                перенаправить пользователя после подтверждения.
        '''
        lst = [email]
        if redirect is not None:
            lst.append(redirect)
        raw_data = self.sep.join(lst)
        return super().generate_token(raw_data)

    def confirm_token(self, token):
        '''
        Проверяет цифровую сигнатуру письма.
        Возвращает подписанные в виде словаря с двумя ключами ('email' и
        'redirect', если он присутствует) или False, если подпись невалидна.

        Аргументы:
            token(str, необходимо): строка, содержащая сигнатуру, которую
                необходимо проверить и разбить на данные.
        '''
        raw_data = super().confirm_token(token)
        if raw_data is False:
            return False
        else:
            data = raw_data.split(self.sep)
            if len(data) == 2:
                return {'email': data[0], 'redirect': data[1]}
            else:
                return {'email': data[0]}

    def load_template(self, name):
        '''
        Возвращает загруженный шаблон jinja2.

        Аргументы:
            name(str, необходимо): имя файла с шаблоном, лежащего в
                папке cyberdas/templates
        '''
        template_path = path.join('cyberdas/templates', name + '.jinja2')
        with open(path.abspath(template_path), 'r') as fp:
            return jinja2.Template(fp.read())
