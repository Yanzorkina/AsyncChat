from __main__ import __file__ as where_am_i
import log.client_log_config as of_client
import log.server_log_config as of_server
import inspect

if where_am_i.endswith('server.py'):
    LOGGER = of_server.LOGGER
if where_am_i.endswith('client.py'):
    LOGGER = of_client.LOGGER


def log(function):
    def wrap(*args, **kwargs):
        func_var = function(*args, *kwargs)
        caller_name = inspect.currentframe().f_back.f_code.co_name
        LOGGER.debug(f'Функция {function.__name__} вызвана из функции {caller_name}')
        return func_var
    return wrap
