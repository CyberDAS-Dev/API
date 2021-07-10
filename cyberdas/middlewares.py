import falcon_sqla
from sqlalchemy import create_engine

def create_db_middleware(cfg):
    '''
    Возвращает БД-middleware, ответственное за управление сессиями базы данных.
    Сессия будет доступна в каждом запросе через req.context.session.
    '''
    engine = create_engine(cfg['alembic']['sqlalchemy.url'])
    return falcon_sqla.Manager(engine).middleware


def middleware(api):
    '''
    Функция, инициализирующая все middleware проекта.
    Каждая строка должна быть вида 'api.add_middleware(*middleware*)'
    
    Внимание: порядок важен! Эти компоненты не независимы, первый в списке будет
    первым при обработке запросов. Например, аутентификационный middleware не сможет
    работать без middleware базы данных, поэтому компонент для БД должен идти первее 
    '''
    api.add_middleware(create_db_middleware(api.cfg))
