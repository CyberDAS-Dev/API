from .mail import Mail
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

    def new_transaction(self, sender, subject, template, transaction, expires):
        return TransactionMail(self.cfg, sender, subject, template,
                               self.frontend, transaction, expires)
