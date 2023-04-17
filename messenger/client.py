import argparse
import os
import sys
import json
import socket
import threading
import time
from os.path import join, dirname
from dotenv import load_dotenv
from common.common_functions import get_message, send_message
from log.client_log_config import LOGGER
from AsyncChat.messenger.common.wrap import log
from AsyncChat.messenger.common.metaclass_client import ClientMaker
from common.jim_variables import *
from database.client_database import ClientDatabase

CLIENT_LOGGER = LOGGER

# Будем обращаться к серверу и базе данных только в контекстах
sock_lock = threading.Lock()
database_lock = threading.Lock()


class ClientSender(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    @log
    def create_exit_message(self):
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

    @log
    def create_message(self):
        to_user = input('Введите имя получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')

        # Проверка существования пользователя
        with database_lock:
            if not self.database.check_user(to_user):
                CLIENT_LOGGER.error(f'Невозможно отправить сообщение несуществующему пользователю {to_user}')
                return

        message_dict = {
            ACTION: MESSAGE,
            TIME: time.time(),
            SENDER: self.account_name,
            MESSAGE_TEXT: message,
            DESTINATION: to_user
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')

        # Сохранение сообщения в базе клиента
        with database_lock:
            self.database.save_message(self.account_name, to_user, message)

        with sock_lock:
            try:
                send_message(self.sock, message_dict)
                CLIENT_LOGGER.info(f'Отпрвлено сообщение для {to_user}')
            except Exception as e:
                CLIENT_LOGGER.critical(f'Потеряно соединение с сервером. {e}')
                sys.exit(1)

    def get_contacts(self):
        message_dict = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            CHAT_USER: self.account_name
        }
        CLIENT_LOGGER.debug(f'Сформирован запрос на список контактов: {message_dict}')
        try:
            send_message(self.sock, message_dict)
            CLIENT_LOGGER.info(f'Отпрвлено сообщение на сервер с запросом контактов для {self.account_name}')
        except Exception as e:
            CLIENT_LOGGER.critical(f'Потеряно соединение с сервером. {e}')
            sys.exit(1)

    def add_contact(self):
        who_to_add = input("Какого пользователя вы хотите добавить?")
        message_dict = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            CHAT_USER: self.account_name,
            TARGET_USER: who_to_add
        }
        CLIENT_LOGGER.debug(f'Сформирован запрос на добавление контакта: {message_dict}')
        try:
            send_message(self.sock, message_dict)
            CLIENT_LOGGER.info(f'Отпрвлено сообщение на сервер с запросом на добавление  {who_to_add}')
        except Exception as e:
            CLIENT_LOGGER.critical(f'Потеряно соединение с сервером. {e}')
            sys.exit(1)

    # пока не DRY
    def del_contact(self):
        will_be_removed = input("Какого пользователя вы хотите добавить?")
        message_dict = {
            ACTION: DEL_CONTACT,
            TIME: time.time(),
            CHAT_USER: self.account_name,
            TARGET_USER: will_be_removed
        }
        CLIENT_LOGGER.debug(f'Сформирован запрос на удаление контакта: {message_dict}')
        try:
            send_message(self.sock, message_dict)
            CLIENT_LOGGER.info(f'Отпрвлено сообщение на сервер с запросом на удаление  {will_be_removed}')
        except Exception as e:
            CLIENT_LOGGER.critical(f'Потеряно соединение с сервером. {e}')
            sys.exit(1)

    @log
    def run(self):  # user_interactive
        print('message - режим отправки сообщения \nexit - выход из программы')
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message()
            elif command == 'exit':
                send_message(self.sock, self.create_exit_message())
                print('Завершение соединения.')
                CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
                time.sleep(0.5)
                break
            elif command == 'get_contacts':
                self.get_contacts()
            elif command == 'add_contact':
                self.add_contact()
            elif command == 'del_contact':
                self.del_contact()

            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')


class ClientReader(threading.Thread, metaclass=ClientMaker):
    def __init__(self, account_name, sock):
        self.account_name = account_name
        self.sock = sock
        super().__init__()

    @log
    def run(self):  # message_from_server
        while True:
            try:
                message = get_message(self.sock)
                if ACTION in message and message[
                    ACTION] == MESSAGE and SENDER in message and DESTINATION in message and MESSAGE_TEXT in message and \
                        message[DESTINATION] == self.account_name:
                    print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    CLIENT_LOGGER.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                else:
                    CLIENT_LOGGER.error(f'Получено некорректное сообщение от сервера:{message}')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                break


@log
def create_presence(account_name='Guest'):
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        CHAT_USER: {
            ACCOUNT_NAME: account_name
        }
    }
    CLIENT_LOGGER.debug(f'Создано {PRESENCE} сообщение для {account_name}')
    return out


@log
def process_ans(message):
    CLIENT_LOGGER.debug(f'Анализ сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        return f'400 : {message[ERROR]}'
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
        reciever = ClientReader(client_name, transport)
        reciever.daemon = True
        reciever.start()

        # Отправка сообщений и меню
        user_interface = ClientSender(client_name, transport)
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
