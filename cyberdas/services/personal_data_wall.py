import falcon

from cyberdas.models import User
from cyberdas.exceptions import HTTPNotEnoughPersonalData


class required_personal_data:
    '''
    Инициализируемая функция, используемая как хук перед запросом.
    Проверяет, что пользователь, совершающий запрос, указал достаточно
    персональных данных в профиле для его выполнения.

    Аргументы инициализации:
        required_fields(list, необходим): список строк с названиями полей из
            модели данных пользователя, необходимых для совершения запроса
    '''

    def __init__(self, required_fields):
        self.required_fields = required_fields

    def __call__(self, req: falcon.Request, resp: falcon.Response, resource, params): # noqa
        uid = req.context.user['uid']
        user = req.context.session.query(User).filter_by(id = uid).first()

        absent_fields = []
        for field in self.required_fields:
            if getattr(user, field) is None:
                absent_fields.append(field)

        if len(absent_fields) > 0:
            req.context.logger.debug('[PD_WALL] uid %s, absent %s'
                                     % (uid, ':'.join(absent_fields)))
            raise HTTPNotEnoughPersonalData(absent_fields)
