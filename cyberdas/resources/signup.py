import json
from os import path

import jinja2
import falcon
from falcon.media.validators import jsonschema

from cyberdas.models import User, Faculty


class Signup(object):

    with open(path.abspath('cyberdas/static/signup_schema.json'), 'r') as f:
        signup_schema = json.load(f)

    def __init__(self, mail_service, testing = False):
        self.mail = mail_service
        self._testing = testing

    @jsonschema.validate(signup_schema)
    def on_post(self, req, resp):
        '''
        Обрабатывает запрос на регистрацию, и, в случае корректности данных,
        регистрирует пользователя и отправляет письмо для подтверждения
        адреса почты.

        Требует JSON во входящем потоке.
        '''
        dbses = req.context.session
        log = req.context.logger

        data = req.get_media()

        user = dbses.query(User).filter_by(email = data['email']).first()
        if user is not None:
            raise falcon.HTTPForbidden(
                title = '403 Forbidden',
                description = 'Такой адрес почты уже занят.'
            )
        faculty = dbses.query(Faculty).filter_by(name = data['faculty']).first()
        if faculty is None:
            raise falcon.HTTPBadRequest

        newUser = User(
            email = data['email'], password = data['password'],
            name = data['name'], surname = data['surname'],
            patronymic = (data['patronymic'] if 'patronymic' in data.keys()
                          else None),
            faculty_id = faculty.id, email_verified = False, verified = False
        )
        dbses.add(newUser)
        log.debug('[НОВЫЙ ПОЛЬЗОВАТЕЛЬ] email %s' % data['email'])

        mail_token = self.mail.generate_token(data['email'])
        verify_url = f'{req.forwarded_prefix}/verify?token={mail_token}'
        template = self.load_template('verify_email')
        rendered_template = template.render(verify_url = verify_url)

        self.mail.send(
            to = data['email'],
            subject = 'Подтверждение e-mail адреса в CyberDAS',
            content = rendered_template
        )
        log.debug('[ОТПРАВЛЕН EMAIL] email %s, link %s' % (data['email'],
                                                           verify_url))
        resp.status = falcon.HTTP_200

    def load_template(self, name):
        '''
        Возвращает загруженный шаблон jinja2.
        '''
        template_path = path.join('cyberdas/templates', name + '.jinja2')
        with open(path.abspath(template_path), 'r') as fp:
            return jinja2.Template(fp.read())
