import json

import falcon_sqla
from sqlalchemy import create_engine

from .. import models
from .. import config


def setup_faculties(dbsession):
    '''
    Загрузка списка факультетов в БД.
    '''
    with open("cyberdas/static/faculties.json") as f:
        data = json.load(f)

    for entry in data:
        newFaculty = models.Faculty(
            id = entry['id'],
            name = entry['name']
        )
        dbsession.add(newFaculty)


def main():
    cfg = config.get_cfg()
    engine = create_engine(cfg['alembic']['sqlalchemy.url'])
    manager = falcon_sqla.Manager(engine)

    print("[ Инициализация БД ]")
    print("Удаление существующей модели данных...", end=' ')
    models.Base.metadata.drop_all(engine)
    print("Готово")
    print("Установка новой модели данных...", end=' ')
    models.Base.metadata.create_all(engine)
    print("Готово")

    with manager.session_scope() as session:
        print("Загрузка списка факультетов...", end=' ')
        setup_faculties(session)
        print("Готово")
