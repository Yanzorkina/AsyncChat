import os
import select
import socket
import sys
import json
import time
from os.path import join, dirname
from dotenv import load_dotenv
from common_functions import get_message, send_message
from log.server_log_config import LOGGER
from wrap import log

SERVER_LOGGER = LOGGER


@log
def process_client_message(message, messages_list, client):
    SERVER_LOGGER.debug(f'Получено сообщение от клиента: {message}')
    if not (not (os.environ.get("ACTION") in message) or not (message[os.environ.get("ACTION")] == os.environ.get(
            "PRESENCE")) or not (os.environ.get("TIME") in message) or not (os.environ.get("USER") in message) or not (
            message[os.environ.get("USER")][os.environ.get("ACCOUNT_NAME")] == 'Guest')):
        send_message(client, {os.environ.get("RESPONSE"): 200})
        return
    elif os.environ.get("ACTION") in message and message[os.environ.get("ACTION")] == os.environ.get(
            "MESSAGE") and os.environ.get("TIME") in message and os.environ.get("MESSAGE_TEXT") in message:
        messages_list.append((message[os.environ.get("ACCOUNT_NAME")], message[os.environ.get("MESSAGE_TEXT")]))
        return
    else:
        send_message(client, {os.environ.get("RESPONSE"): 400, os.environ.get("ERROR"): 'Bad Request'})
        return


def main():
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            listen_port = os.environ.get("DEFAULT_PORT")
        if int(listen_port) < 1024 or int(listen_port) > 65535:
            SERVER_LOGGER.critical(f'Попытка использования недопустимого порта {listen_port}')
            sys.exit(1)
    except IndexError:
        print('После параметра -\'p\' необходимо указать номер порта.')
        sys.exit(1)
    except ValueError:
        print(
            'В качастве порта может быть указано только число в диапазоне от 1024 до 65535.')
        sys.exit(1)

    try:
        if '-a' in sys.argv:
            listen_address = sys.argv[sys.argv.index('-a') + 1]
            SERVER_LOGGER.info(f'Сервер запущен. Порт подлючения {listen_port}, адрес подключения: {listen_address}')

        else:
            listen_address = ''
            SERVER_LOGGER.info(f'Сервер запущен. Порт подлючения {listen_port}, прием с любых адресов')

    except IndexError:
        print(
            'В случае указания параметра \'a\'- необходимо указать адрес.')
        sys.exit(1)

    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.bind((listen_address, int(listen_port)))
    transport.settimeout(0.5)

    clients = []
    messages = []

    transport.listen(int(os.environ.get("MAX_CONNECTIONS")))

    while True:
        try:
            client, client_address = transport.accept()
        except OSError:
            pass
        else:
            LOGGER.info(f'Соединение {client_address} с установлено')
            clients.append(client)

        recv_data_list = []
        send_data_list = []
        error_list = []

        try:
            if clients:
                recv_data_list, send_data_list, error_list = select.select(clients, clients, [], 0)
        except OSError:
            pass

        if recv_data_list:
            for client_with_message in recv_data_list:
                try:
                    process_client_message(get_message(client_with_message), messages, client_with_message)
                except Exception as e:
                    # print(e, 'строка 97')  # какая ошибка
                    LOGGER.info(f'{client_with_message.getpeername()} отключился.')
                    clients.remove(client_with_message)

        if messages and send_data_list:
            message = {
                os.environ.get("ACTION"): os.environ.get("MESSAGE"),
                os.environ.get("SENDER"): messages[0][0],
                os.environ.get("TIME"): time.time(),
                os.environ.get("MESSAGE_TEXT"): messages[0][1]
            }
            del messages[0]
            for waiting_client in send_data_list:
                try:
                    send_message(waiting_client, message)
                except Exception as e:
                    # print(e, 'строка 113')
                    LOGGER.info(f'{waiting_client.getpeername()} отключился.')
                    clients.remove(waiting_client)


if __name__ == '__main__':
    main()
