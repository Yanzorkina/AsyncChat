import sys
import os
import logging.handlers
from .log_config import FILE_LOGGING_LEVEL, STREAM_LOGGING_LEVEL, SERVER_FORMAT

sys.path.append('../')

SERVER_FORMATTER = logging.Formatter(SERVER_FORMAT)
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'server.log')

STREAM_HANDLER = logging.StreamHandler(sys.stderr)
STREAM_HANDLER.setFormatter(SERVER_FORMATTER)
STREAM_HANDLER.setLevel(STREAM_LOGGING_LEVEL)
LOG_FILE = logging.handlers.TimedRotatingFileHandler(PATH, encoding='utf8', interval=1, when='D')
LOG_FILE.setFormatter(SERVER_FORMATTER)

LOGGER = logging.getLogger('server')
LOGGER.addHandler(STREAM_HANDLER)
LOGGER.addHandler(LOG_FILE)
LOGGER.setLevel(FILE_LOGGING_LEVEL)

if __name__ == '__main__':
    LOGGER.critical('Критическое событие')
    LOGGER.error('Ошибка')
    LOGGER.info('Инфо')
    LOGGER.debug('Отладка')