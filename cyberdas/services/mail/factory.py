from .mail import Mail
from .template_mail import TemplateMail
from .transaction_mail import TransactionMail


class MailFactory:
    '''
    Класс-фабрика, создающий новых отправителей писем.
    '''

    def __init__(self, cfg):
        self.cfg = cfg
        self.frontend = cfg['internal']['frontend.url']

    def new_simple(self, sender):
        return Mail(self.cfg, sender)

    def new_template(self, sender, subject, template):
        return TemplateMail(self.cfg, sender, subject, template)

    def new_transaction(self, sender, subject, template, transaction, expires):
        return TransactionMail(self.cfg, sender, subject, template,
                               self.frontend, transaction, expires)
