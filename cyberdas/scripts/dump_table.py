import io
import sys
import json
import csv
import argparse

from sqlalchemy import create_engine
import falcon_sqla

from .. import config
from .. import models

parser = argparse.ArgumentParser(description = 'Распечатывает таблицу из БД.')
parser.add_argument('model', type = str,
                    help = 'имя модели данных, таблицу которой надо выгрузить')
parser.add_argument('--json', action = 'store_true',
                    help = 'вернуть таблицу в JSON')
parser.add_argument('--csv', action = 'store_true',
                    help = 'вернуть таблицу в CSV')


def main():
    cfg = config.get_cfg()
    args = parser.parse_args()
    if args.csv and args.json:
        sys.stderr.write("Ошибка: используйте либо --csv, либо --json\n")
        return

    engine = create_engine(cfg['alembic']['sqlalchemy.url'])
    manager = falcon_sqla.Manager(engine)

    model = str.capitalize(args.model)
    if model in dir(models):
        model = eval(f'models.{model}')
    else:
        sys.stderr.write("Ошибка: такой модели данных не существует\n")
        return

    with manager.session_scope() as session:
        results = session.query(model)
        dictionaries = [result.__dict__ for result in results.all()]
        for dct in dictionaries:
            dct.pop('_sa_instance_state')

    if args.csv:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(dictionaries[0].keys())  # шапка
        for obj in dictionaries:
            writer.writerow(obj.values())
        print(output.getvalue())
    elif args.json:
        print(json.dumps(dictionaries, default = str))
    else:
        print(dictionaries)
