import os
import sys
import json
import socket
import time
from os.path import join, dirname
from dotenv import load_dotenv
from common_functions import get_message, send_message
from AsyncChat.messenger.log.client_log_config import LOGGER

CLIENT_LOGGER = LOGGER


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
    message_to_server = create_presence()
    send_message(transport, message_to_server)
    try:
        answer = process_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Ответ от сервера получен {answer}')
        print(answer)
    except (ValueError, json.JSONDecodeError):
        CLIENT_LOGGER.critical('Не удалось декодировать сообщение сервера.')


if __name__ == '__main__':
    main()
