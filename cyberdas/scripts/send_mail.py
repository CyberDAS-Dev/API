import logging
import sys
import argparse

from cyberdas.services import MailFactory
from cyberdas.config import get_cfg

parser = argparse.ArgumentParser(description = 'Разовый отправитель писем.')
parser.add_argument('sender', help = 'отправитель письма',
                    choices = ['signup', 'notify'])
parser.add_argument('to', help = 'адрес почты получателя')
parser.add_argument('subject', help = 'тема письма')
parser.add_argument('--html', type=argparse.FileType('r'),
                    help = 'путь до файла с HTML-содержимым письма')
parser.add_argument('--plain', type=argparse.FileType('r'),
                    help = 'путь до файла с текстовым содержимым письма')
parser.add_argument('--files', nargs = '*',
                    help = 'пути до прикрепленных к письму файлов, через пробел') # noqa
logging.basicConfig(stream = sys.stdout, level = logging.DEBUG)


def main():
    cfg = get_cfg()
    args = parser.parse_args()
    sender = MailFactory(cfg).new_simple(args.sender)
    sender.send(
        args.to, args.subject,
        {'html': args.html.read() if args.html is not None else '',
         'plain': args.plain.read() if args.plain is not None else ''},
        log = logging.getLogger(),
        files = args.files)
