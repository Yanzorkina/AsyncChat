import messenger.log.client_log_config as of_client
import inspect

LOGGER = of_client.LOGGER


def log(function):
    """
    Декоратор, позволяющий логировать вызов функций
    """
    def wrap(*args, **kwargs):
        func_var = function(*args, *kwargs)
        caller_name = inspect.currentframe().f_back.f_code.co_name
        LOGGER.debug(f'Функция {function.__name__} вызвана из функции {caller_name}')
        return func_var
    return wrap
