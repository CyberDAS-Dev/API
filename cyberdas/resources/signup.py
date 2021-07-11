import falcon
import json
import jinja2
import os

from falcon.media.validators import jsonschema

from cyberdas.models import User
from cyberdas.models import Faculty

class Signup(object):

    with open(os.path.abspath('cyberdas/static/signup_schema.json'), 'r') as fp:
            signup_schema = json.load(fp)

    def __init__(self, mail_service, testing = False):
        self.mail = mail_service
        self._testing = testing
    
    @jsonschema.validate(signup_schema)
    def on_post(self, req, resp):
        '''
        Обрабатывает запрос на регистрацию, и, в случае корректности данных, регистрирует пользователя
        и отправляет письмо для подтверждения адреса почты.

        Требует JSON во входящем потоке.
        '''
        dbses = req.context.session

        data = req.get_media()
        
        ### Регистрация
        try:
            user = dbses.query(User).filter_by(email = data['email']).first()
        except: 
            raise falcon.HTTPBadRequest
        if user is not None:
            raise falcon.HTTPForbidden(
                title = '403 Forbidden',
                description = 'Пользователь с такой почтой уже зарегистрирован.')
        
        try: 
            faculty = dbses.query(Faculty).filter_by(name = data['faculty']).first()
            assert faculty is not None
        except:
            raise falcon.HTTPBadRequest
            
        newUser = User(
            email = data['email'], password = data['password'],
            name = data['name'], surname = data['surname'],
            patronymic = (data['patronymic'] if 'patronymic' in data.keys() else None), 
            faculty_id = faculty.id, email_verified = False, verified = False
        )
        dbses.add(newUser)

        ### Отправка письма для верификации адреса
        mail_token = self.mail.generate_token(data['email'])
        if self._testing:
            resp.status = falcon.HTTP_200
            return

        verify_url = '{orig_url}/verify?token={token}'\
                    .format(orig_url = req.forwarded_prefix, token = mail_token)
        template = self.load_template('verify_email')
        rendered_template = template.render(verify_url = verify_url)
        self.mail.send(
            to = data['email'], 
            subject = 'Подтверждение e-mail адреса в CyberDAS', 
            content = rendered_template
        )
        resp.status = falcon.HTTP_200

    def load_template(self, name):
        '''
        Возвращает загруженный шаблон jinja2
        '''
        path = os.path.join('cyberdas/templates', name+'.jinja2')
        with open(os.path.abspath(path), 'r') as fp:
            return jinja2.Template(fp.read())