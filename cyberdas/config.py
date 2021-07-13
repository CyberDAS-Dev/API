import configparser

CONFIG_NAME = 'cfg.ini'


def get_cfg():
    '''
    Возвращает конфигурацию проекта
    '''
    config = configparser.ConfigParser(interpolation = None)
    config.read(CONFIG_NAME)
    return config
