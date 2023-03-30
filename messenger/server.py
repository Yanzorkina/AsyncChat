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
def process_message(message, names, listen_socks):
    if message[os.environ.get("DESTINATION")] in names and names[
        message[os.environ.get("DESTINATION")]] in listen_socks:
        send_message(names[message[os.environ.get("DESTINATION")]], message)
        LOGGER.info(f'Отправлено сообщение пользователю {message[os.environ.get("DESTINATION")]} '
                    f'от пользователя {message[os.environ.get("SENDER")]}.')
    elif message[os.environ.get("DESTINATION")] in names and names[
        message[os.environ.get("DESTINATION")]] not in listen_socks:
        raise ConnectionError
    else:
        LOGGER.error(
            f'Пользователь {message[os.environ.get("DESTINATION")]} не зарегистрирован на сервере, '
            f'отправка сообщения невозможна.')


@log
def process_client_message(message, messages_list, client, clients, names):
    SERVER_LOGGER.debug(f'Получено сообщение от клиента: {message}')
    # Для сообщение о присутствии.
    if os.environ.get("ACTION") in message and message[os.environ.get("ACTION")] == os.environ.get(
            "PRESENCE") and os.environ.get("TIME") in message and os.environ.get("CHAT_USER") in message:
        # Пользователь не зарегестрирован
        if message[os.environ.get("CHAT_USER")][os.environ.get("ACCOUNT_NAME")] not in names.keys():
            names[message[os.environ.get("CHAT_USER")][os.environ.get("ACCOUNT_NAME")]] = client
            send_message(client, {os.environ.get("RESPONSE"): 200})
            print(f"Зарегистрирован пользователь {client}")
        else:
            response = {os.environ.get("RESPONSE"): 400, os.environ.get("ERROR"): None}
            response[os.environ.get("ERROR")] = 'Это имя уже занято'
            send_message(client, response)
            clients.remove(client)
            client.close()
        return
    # Для сообщений с содержимым
    elif os.environ.get("ACTION") in message and message[os.environ.get("ACTION")] == os.environ.get(
            "MESSAGE") and os.environ.get("DESTINATION") in message and os.environ.get(
        "TIME") in message and os.environ.get("SENDER") in message and os.environ.get("MESSAGE_TEXT") in message:
        messages_list.append(message)
        return
    # Если клиент выходит
    elif os.environ.get("ACTION") in message and message[os.environ.get("ACTION")] == os.environ.get(
            "EXIT") and os.environ.get("ACCOUNT_NAME") in message:
        clients.remove(names[message[os.environ.get("ACCOUNT_NAME")]])
        names[message[os.environ.get("ACCOUNT_NAME")]].close()
        del names[message[os.environ.get("ACCOUNT_NAME")]]
        return
    # Иначе отдаём Bad request
    else:
        response = {os.environ.get("RESPONSE"): 400, os.environ.get("ERROR"): None}
        response[os.environ.get("ERROR")] = 'Запрос некорректен.'
        send_message(client, response)
        return


def main():
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    # Парсинг аргументов. Выполняется единожды при запуске.
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

    # Подготовка сокета
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.bind((listen_address, int(listen_port)))
    transport.settimeout(0.5)

    # Список клиентов и сообщений
    clients = []
    messages = []

    # Словарь формата имя_пользяователя : сокет
    names = dict()

    # Прослушивание порта
    transport.listen(int(os.environ.get("MAX_CONNECTIONS")))

    # Главный цикл программы.
    while True:
        try:
            client, client_address = transport.accept()
        except OSError:
            pass
        else:
            SERVER_LOGGER.info(f'Соединение {client_address} с установлено')
            clients.append(client)

        # Списки клиентов в очереди
        recv_data_list = []
        send_data_list = []
        error_list = []

        try:
            if clients:
                recv_data_list, send_data_list, error_list = select.select(clients, clients, [], 0)
        except OSError:
            pass

        # Прием сообщений
        if recv_data_list:
            for client_with_message in recv_data_list:
                try:
                    process_client_message(get_message(client_with_message), messages, client_with_message, clients,
                                           names)
                except Exception as e:
                    # print(e, 'строка 97')  # какая ошибка
                    SERVER_LOGGER.info(f'{client_with_message.getpeername()} отключился.')
                    clients.remove(client_with_message)

        # Обработка сообщений
        for message in messages:
            try:
                process_message(message, names, send_data_list)
            except Exception:
                SERVER_LOGGER.info(f'Связь с {message[os.environ.get("DESTINATION")]} была потеряна')
                clients.remove(names[message[os.environ.get("DESTINATION")]])
                del names[message[os.environ.get("DESTINATION")]]
        messages.clear()


if __name__ == '__main__':
    main()
