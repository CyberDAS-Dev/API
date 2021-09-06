import configparser
import pathlib

CONFIG_NAME = 'cfg.ini'
CONFIG_PATH = pathlib.Path(__file__).parent.parent.resolve().joinpath(CONFIG_NAME) # noqa


def get_cfg():
    '''
    Возвращает конфигурацию проекта
    '''
    config = configparser.ConfigParser(interpolation = None)
    config.read(CONFIG_PATH)
    return config
