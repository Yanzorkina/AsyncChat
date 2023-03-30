import sys
import os
import logging.handlers

from .log_config import FILE_LOGGING_LEVEL, STREAM_LOGGING_LEVEL, CLIENT_FORMAT

sys.path.append('../')

CLIENT_FORMATTER = logging.Formatter(CLIENT_FORMAT)
PATH = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(PATH, 'client.log')

STREAM_HANDLER = logging.StreamHandler(sys.stderr)
STREAM_HANDLER.setFormatter(CLIENT_FORMATTER)
STREAM_HANDLER.setLevel(STREAM_LOGGING_LEVEL)

LOG_FILE = logging.FileHandler(PATH, encoding='utf8')
LOG_FILE.setFormatter(CLIENT_FORMATTER)

LOGGER = logging.getLogger('client')
LOGGER.addHandler(STREAM_HANDLER)
LOGGER.addHandler(LOG_FILE)
LOGGER.setLevel(FILE_LOGGING_LEVEL)


if __name__ == '__main__':
    LOGGER.critical('Критическое событие')
    LOGGER.error('Ошибка')
    LOGGER.info('Инфо')
    LOGGER.debug('Отладка')
