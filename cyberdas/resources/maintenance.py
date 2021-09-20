import json
from os import path

import falcon
from falcon.media.validators import jsonschema

from cyberdas.models import User, Maintenance
from cyberdas.services import support_ott, required_personal_data


class MaintenanceCollection:

    auth = {'disabled': 1}

    with open(path.abspath('cyberdas/static/maintenance_schema.json')) as f:
        maintenance_schema = json.load(f)

    @jsonschema.validate(maintenance_schema)
    @falcon.before(support_ott)
    @falcon.before(required_personal_data(['building', 'room']))
    def on_post(self, req, resp):
        '''
        Создает новую заявку на оказание технических услуг.

        Параметры:
            category (required, in: body) - категория услуг, одна из ['plumber',
                'carpenter', 'electrician']

            text (required, in: body) - содержание заявки
        '''
        dbses = req.context.session
        log = req.context.logger
        uid = req.context.user['uid']

        # Получаем пользовательские данные
        data = req.get_media()

        user = dbses.query(User).filter_by(id = uid).first()
        bld, room = user.building, user.room

        # Добавляем обращение в базу данных
        new_item = Maintenance(building = bld, room = room, user_id = uid,
                               **data)
        dbses.add(new_item)
        dbses.flush()

        log.info('[MAINTENANCE][НОВЫЙ] category %s, id %s' % (data['category'],
                                                              new_item.id))
        resp.status = falcon.HTTP_201
