import argparse
import os
import sys
import json
import socket
import threading
import time
from os.path import join, dirname
from dotenv import load_dotenv
from common_functions import get_message, send_message
from log.client_log_config import LOGGER
from wrap import log

CLIENT_LOGGER = LOGGER


@log
def create_exit_message(account_name):
    return {
        os.environ.get("ACTION"): os.environ.get("EXIT"),
        os.environ.get("TIME"): time.time(),
        os.environ.get("ACCOUNT_NAME"): account_name
    }


@log
def message_from_server(sock, my_username):
    while True:
        try:
            message = get_message(sock)
            if os.environ.get("ACTION") in message and message[os.environ.get("ACTION")] == os.environ.get(
                    "MESSAGE") and os.environ.get("SENDER") in message and os.environ.get(
                "DESTINATION") in message and os.environ.get("MESSAGE_TEXT") in message and message[
                os.environ.get("DESTINATION")] == my_username:
                print(
                    f'\nПолучено сообщение от пользователя {message[os.environ.get("SENDER")]}:\n{message[os.environ.get("MESSAGE_TEXT")]}')
                CLIENT_LOGGER.info(
                    f'Получено сообщение от пользователя {message[os.environ.get("SENDER")]}:\n{message[os.environ.get("MESSAGE_TEXT")]}')
            else:
                CLIENT_LOGGER.error(f'Получено некорректное сообщение от сервера:{message}')
        except (OSError, ConnectionError, ConnectionAbortedError,
                ConnectionResetError, json.JSONDecodeError):
            CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
            break


@log
def create_message(sock, account_name='Guest'):
    to_user = input('Введите имя получателя сообщения: ')
    message = input('Введите сообщение для отправки: ')
    message_dict = {
        os.environ.get("ACTION"): os.environ.get("MESSAGE"),
        os.environ.get("TIME"): time.time(),
        os.environ.get("SENDER"): account_name,
        os.environ.get("MESSAGE_TEXT"): message,
        os.environ.get("DESTINATION"): to_user
    }
    CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
    try:
        send_message(sock, message_dict)
        CLIENT_LOGGER.info(f'Отпрвлено сообщение для {to_user}')
    except Exception as e:
        CLIENT_LOGGER.critical(f'Потеряно соединение с сервером. {e}')
        sys.exit(1)


@log
def user_interactive(sock, username):
    print('message - режим отправки сообщения \nexit - выход из программы')
    while True:
        command = input('Введите команду: ')
        if command == 'message':
            create_message(sock, username)
        elif command == 'exit':
            send_message(sock, create_exit_message(username))
            print('Завершение соединения.')
            CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
            time.sleep(0.5)
            break
        else:
            print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')


@log
def create_presence(account_name='Guest'):
    out = {
        os.environ.get("ACTION"): os.environ.get("PRESENCE"),
        os.environ.get("TIME"): time.time(),
        os.environ.get("CHAT_USER"): {
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
        parser = argparse.ArgumentParser()
        parser.add_argument('addr', default=os.environ.get("DEFAULT_IP_ADDRESS"), nargs='?')
        parser.add_argument('port', default=os.environ.get("DEFAULT_PORT"), type=int, nargs='?')
        parser.add_argument('-n', '--name', default=None, nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        server_address = namespace.addr
        server_port = namespace.port
        client_name = namespace.name
        if not client_name:
            client_name = input('Введите свое имя: ')
        CLIENT_LOGGER.info(
            f'Клиент запущен. Адрес сервера:{server_address}, порт:{server_port}, пользователь {client_name}')
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
    send_message(transport, create_presence(client_name))
    try:
        answer = process_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Ответ от сервера получен {answer}')
        print(answer)
    except (ValueError, json.JSONDecodeError):
        CLIENT_LOGGER.critical('Не удалось декодировать сообщение сервера.')
    except Exception as e:
        CLIENT_LOGGER.critical(f'Возникла ошибка: {e}')
        sys.exit(1)
    else:
        # Прием сообщений
        reciever = threading.Thread(target=message_from_server, args=(transport, client_name))
        reciever.daemon = True
        reciever.start()

        # Отправка сообщений и меню
        user_interface = threading.Thread(target=user_interactive, args=(transport, client_name))
        user_interface.daemon = True
        user_interface.start()
        CLIENT_LOGGER.debug('Процессы запущены')

        while True:
            time.sleep(1)
            if reciever.is_alive() and user_interface.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
