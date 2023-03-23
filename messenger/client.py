import os
import sys
import json
import socket
import time
from os.path import join, dirname
from dotenv import load_dotenv
from common_functions import get_message, send_message
from log.client_log_config import LOGGER
from wrap import log

CLIENT_LOGGER = LOGGER


@log
def message_from_server(message):
    if os.environ.get("ACTION") in message and message[os.environ.get("ACTION")] == os.environ.get(
            "MESSAGE") and os.environ.get("SENDER") in message and os.environ.get("MESSAGE_TEXT") in message:
        print(f'Сообшение от {message[os.environ.get("SENDER")]}: {message[os.environ.get("MESSAGE_TEXT")]}')
        CLIENT_LOGGER.info(
            f'Сообшение от {message[os.environ.get("SENDER")]}: {message[os.environ.get("MESSAGE_TEXT")]}')
    else:
        CLIENT_LOGGER.error(f'Некорректное сообщение с сервера: {message}')


@log
def create_message(sock, account_name='Guest'):
    message = input('Введите сообщение для отправки или \'exit\' для завершения работы: ')
    if message == 'exit':
        sock.close()
        LOGGER.info('Завершение работы по команде пользователя.')
        print('Вы вышли.')
        sys.exit(0)
    message_dict = {
        os.environ.get("ACTION"): os.environ.get("MESSAGE"),
        os.environ.get("TIME"): time.time(),
        os.environ.get("ACCOUNT_NAME"): account_name,
        os.environ.get("MESSAGE_TEXT"): message
    }
    LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
    return message_dict


@log
def create_presence(account_name='Guest'):
    out = {
        os.environ.get("ACTION"): os.environ.get("PRESENCE"),
        os.environ.get("TIME"): time.time(),
        os.environ.get("USER"): {
            os.environ.get("ACCOUNT_NAME"): account_name
        }
    }
    CLIENT_LOGGER.debug(f'Создано {os.environ.get("PRESENCE")} сообщение для {account_name}')
    return out


@log
def process_ans(message):
    CLIENT_LOGGER.debug(f'Анализ сообщения от сервера: {message}')
    if os.environ.get("RESPONSE") in message:
        if message[os.environ.get("RESPONSE")] == 200:
            return '200 : OK'
        return f'400 : {message[os.environ.get("ERROR")]}'
    raise ValueError


def main():
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
    try:
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        client_mode = sys.argv[3]
        CLIENT_LOGGER.info(
            f'Клиент запущен. Адрес сервера:{server_address}, порт:{server_port}, режим работы: {client_mode}')
        if server_port < 1024 or server_port > 65535:
            CLIENT_LOGGER.critical(f'Попытка использования недопустимого порта {server_port}')
            sys.exit(1)
        CLIENT_LOGGER.info(f'Клиент запущен. Адрес: {server_address}, порт: {server_port}')
    except IndexError:
        server_address = os.environ.get("DEFAULT_IP_ADDRESS")
        server_port = os.environ.get("DEFAULT_PORT")
    except ValueError:
        print('Укажите порт от 1024 до 65535.')
        sys.exit(1)

    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.connect((server_address, int(server_port)))
    send_message(transport, create_presence())
    try:
        answer = process_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Ответ от сервера получен {answer}')
        print(answer)
    except (ValueError, json.JSONDecodeError):
        CLIENT_LOGGER.critical('Не удалось декодировать сообщение сервера.')

    while True:
        if client_mode == 'send':
            try:
                send_message(transport, create_message(transport))
            except (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
                CLIENT_LOGGER.error(f"Соединение с сервером {server_address} потеряно.")
                sys.exit()

        if client_mode == 'listen':
            try:
                message_from_server(get_message(transport))
            except (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
                CLIENT_LOGGER.error(f"Соединение с сервером {server_address} потеряно.")
                sys.exit()


if __name__ == '__main__':
    main()
