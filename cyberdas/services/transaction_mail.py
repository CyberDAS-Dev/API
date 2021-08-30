from ..utils.load_template import load_template
from .mail import Mail


class TransactionMailFactory:
    '''
    Класс-фабрика, создающий новых отправителей транзакционных писем.
    '''

    def __init__(self, cfg):
        self.cfg = cfg
        self.frontend = cfg['internal']['frontend.url']

    def new(self, sender, subject, template, transaction, expires):
        return TransactionMail(self.cfg, sender, subject, template,
                               self.frontend, transaction, expires)


class TransactionMail(Mail):
    '''
    Класс, позволяющий отправлять транзакционные эмэйлы с подписанными данными.
    '''

    def __init__(self, cfg, sender, subject, template, frontend, transaction, expires): # noqa
        super().__init__(cfg, sender)
        self.sep = ';'  # используется как разделитель при сериализации
        self.frontend_url = frontend
        self.subject = subject
        self.template = template
        self.transaction_url = transaction
        self.expires = expires

    def send(self, req, to, data, template_data = {}, transaction_url = None):
        '''
        Отправляет письмо с подтверждением некоторого действия на указанный
        ящик и возвращает URL, подставленный в шаблон письма.

        Аргументы:
            req(необходим): входящий запрос, из него извлекаются параметры
                для переадресации.

            to(string, необходим): адрес почты, на которую нужно отправить
                письмо.

            data(dict, необходим): словарь с размеченными данными для отправки
                в токене и последующего использования на валидационном эндпоинте

            template_data(dict, опционально): словарь с данными для заполнения
                шаблона письма.

            transaction_url(string, опционально): строка, позволяющая переписать
                транзакционный URL для конкретного письма.
        '''
        token = self.generate_token(data)
        _transaction_url = transaction_url or self.transaction_url

        # Если клиент предоставил 'next', то перенаправляем его на фронтенд
        next = req.get_param('next')
        backend_url = f'{req.forwarded_prefix}/{_transaction_url}'
        if next is not None:
            url = f'{self.frontend_url}/{next}?token={token}&backend={backend_url}' # noqa
        # Иначе, отправляем клиента сразу на валидационный эндпоинт на бэкенде
        else:
            url = f'{backend_url}?token={token}'

        # Рендерим шаблоны письма (HTML и текстовый)
        html_template = load_template(self.template).render(transaction_url = url, **template_data) # noqa
        plain_template = load_template(self.template+'_plain').render(transaction_url = url, **template_data) # noqa

        # Отправляем письмо
        super().send(
            to = to,
            subject = self.subject,
            content = {'html': html_template, 'plain': plain_template},
            log = req.context.logger
        )
        return url

    def confirm_token(self, token):
        return super().confirm_token(token, self.expires)
