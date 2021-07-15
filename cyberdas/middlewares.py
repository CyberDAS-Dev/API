import falcon_sqla
from sqlalchemy import create_engine

from .middleware import logging, session


def create_logging_middleware(cfg):
    '''
    Инициализирует логгирующий middleware, ответственный за запись всех
    входящих запросов и внутренних сообщений от компонентов.
    Доступ к внутреннему логгеру осуществляется через req.context.logger.
    '''
    return logging.LoggerMiddleware(cfg)


def create_db_middleware(cfg):
    '''
    Инициализирует БД-middleware, ответственный за управление сессиями к БД.
    Сессия будет доступна в каждом запросе через req.context.session.
    '''
    engine = create_engine(cfg['alembic']['sqlalchemy.url'])
    return falcon_sqla.Manager(engine).middleware


def create_session_middleware(api):
    '''
    Инициализирует сессионный middleware, ответственный за управление
    аутентификацией пользователей. Пользовательская сессия будет доступна в
    каждом запросе через req.context.user.
    '''
    return session.SessionMiddleware(api, exempt_routes = [])


def middleware(api):
    '''
    Функция, инициализирующая все middleware проекта.
    Каждая строка должна быть вида 'api.add_middleware(*middleware*)'

    Внимание: порядок важен! Middleware-компоненты не независимы, при этом
    первый компонент в этой функции будет первым при обработке запросов.
    Например, аутентификационный middleware не сможет работать без middleware
    базы данных, поэтому компонент для БД должен идти первым.
    '''
    api.add_middleware(create_db_middleware(api.cfg))
    api.add_middleware(create_logging_middleware(api.cfg))
    api.add_middleware(create_session_middleware(api))
