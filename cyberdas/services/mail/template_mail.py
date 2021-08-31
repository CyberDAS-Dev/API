from cyberdas.utils.load_template import load_template
from .mail import Mail


class TemplateMail(Mail):
    '''
    Класс, позволяющий отправлять письма по заранее заданному шаблону.
    '''

    def __init__(self, cfg, sender, subject, template):
        super().__init__(cfg, sender)
        self.subject = subject
        self.template = template

    def send(self, to, logger, template_data = {}):
        '''
        Отправляет письмо по шаблону на предоставленный ящик. Если в нем есть
        что заполнять, то может заполнить его с помощью предоставленных данных.

        Аргументы:
            to(string, необходим): адрес почты, на которую нужно отправить
                письмо.

            logger(logging.Logger, необходим): логгер для записи почтовых
                логов.

            template_data(dict, опционально): словарь с данными для заполнения
                шаблона письма.
        '''
        # Рендерим шаблоны письма (HTML и текстовый)
        html_template = load_template(self.template).render(**template_data)
        plain_template = load_template(self.template+'_plain').render(**template_data) # noqa

        # Отправляем письмо
        super().send(
            to = to,
            subject = self.subject,
            content = {'html': html_template, 'plain': plain_template},
            log = logger
        )
