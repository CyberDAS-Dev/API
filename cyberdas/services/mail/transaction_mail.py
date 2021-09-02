from .template_mail import TemplateMail


class TransactionMail(TemplateMail):
    '''
    Класс, позволяющий отправлять транзакционные эмэйлы с подписанными данными.
    '''

    def __init__(self, cfg, sender, subject, template, frontend, transaction, expires): # noqa
        super().__init__(cfg, sender, subject, template)
        self.frontend_url = frontend
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
        if next is not None:
            url = f'{self.frontend_url}/{next}?token={token}&backend={_transaction_url}' # noqa
        # Иначе, отправляем клиента сразу на валидационный эндпоинт на бэкенде
        else:
            url = f'{req.forwarded_prefix}/{_transaction_url}?token={token}'

        # Отправляем письмо
        super().send(
            to = to,
            logger = req.context.logger,
            template_data = {'transaction_url': url, **template_data}
        )
        return url

    def confirm_token(self, token):
        return super().confirm_token(token, self.expires)
