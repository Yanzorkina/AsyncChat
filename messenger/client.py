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
from common.jim_variables import *
from messenger.common.wrap import log
from messenger.common.metaclass_client import ClientMaker
from database.client_database import ClientDatabase

# Инициализация логгера
CLIENT_LOGGER = LOGGER

# Функции будут принимать ответы самостоятельно, поэтому нужно под них блокировать сокет и БД для транзакций.
sock_lock = threading.Lock()
database_lock = threading.Lock()

class ClientSender(threading.Thread, metaclass=ClientMaker):
    # """
    # Класс, отвечающий за реализацию действий пользователя - отправка, запросы
    # """
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    @log
    def create_exit_message(self):
        """
        Функция отправляющая сообщение о выходе клиента
        """
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.account_name
        }

    @log
    def create_message(self):
        """
        Функция отправки сообщения другому пользователю
        """
        to_user = input('Введите имя получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')

        with database_lock:
            if not self.database.check_user(to_user):
                CLIENT_LOGGER.error(f"Попытка отправить сообщение незарегистрированному пользователю: {to_user}")
                return
        message_dict = {
            ACTION: MESSAGE,
            TIME: time.time(),
            SENDER: self.account_name,
            MESSAGE_TEXT: message,
            DESTINATION: to_user
        }
        CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')

        # Сохранение сообщения в истории
        with database_lock:
            self.database.save_message(self.account_name, to_user, message)

        # Дожидаемся сокет и отправляем сообщение
        with sock_lock:
            try:
                send_message(self.sock, message_dict)
                CLIENT_LOGGER.info(f'Отпрвлено сообщение для {to_user}')
            except OSError as e:
                if e.errno:
                    CLIENT_LOGGER.critical(f'Потеряно соединение с сервером. {e}')
                    sys.exit(1)
                else:
                    CLIENT_LOGGER.error('Не удалось передать сообщение. Таймаут соединения')

    def run(self):
        """
        Главная функция, запрашивает команды и запускает соответствующие функции
        """
        self.print_help()
        while True:
            command = input('Введите команду: ')
            # Отправка сообщений другим пользователям
            if command == 'message':
                self.create_message()

            # Помощь
            elif command == 'help':
                self.print_help()

            # Корректный Выход. Отправляем сообщение серверу о выходе.
            elif command == 'exit':
                with sock_lock:
                    try:
                        send_message(self.sock, self.create_exit_message)
                    except:
                        pass
                    print('Завершение соединения.')
                    CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
                # Задержка для отправки сообщения до выхода
                time.sleep(1)
                break

            # Список контактов
            elif command == 'contacts':
                with database_lock:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)

            # Редактирование контактов
            elif command == 'edit':
                self.edit_contacts()

            # история сообщений.
            elif command == 'history':
                self.print_history()

            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    def print_help(self):
        """
        Функуция-справка. Выводит в консоль список доступных команд
        """
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('history - история сообщений')
        print('contacts - список контактов')
        print('edit - редактирование списка контактов')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    def print_history(self):
        '''
        Функция выводит сообщения из локальной базы данных пользователя.
        '''
        ask = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock:
            if ask == 'in':
                history_list = self.database.get_history(to_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} от {message[3]}:\n{message[2]}')
            elif ask == 'out':
                history_list = self.database.get_history(from_who=self.account_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} от {message[3]}:\n{message[2]}')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]}, пользователю {message[1]}\
                        от {message[3]}\n{message[2]}')


    def edit_contacts(self):
        """
        Функция изменеия контактов. Позволяет добавить или удалить контакт.
        """
        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            edit = input('Введите имя удаляемного контакта: ')
            with database_lock:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    CLIENT_LOGGER.error('Попытка удаления несуществующего контакта.')
        elif ans == 'add':
            # Проверка на возможность такого контакта
            edit = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(edit):
                with database_lock:
                    self.database.add_contact(edit)
                with sock_lock:
                    try:
                        add_contact(self.sock, self.account_name, edit)
                    except Exception as e:
                        CLIENT_LOGGER.error(f'Не удалось отправить информацию на сервер. {e}')


class ClientReader(threading.Thread, metaclass=ClientMaker):
    # """
    # Класс, отвечающий за прием сообщений с сервера. Принимает сообщения, выводит в консоль , сохраняет в базу.
    # """
    def __init__(self, account_name, sock, database):
        self.account_name = account_name
        self.sock = sock
        self.database = database
        super().__init__()

    def run(self):
        """
        Основной цикл приёмника сообщений, принимает сообщения, выводит в консоль. Завершается при потере соединения.
        """
        while True:
            time.sleep(1)
            with sock_lock:
                try:
                    message = get_message(self.sock)

                # Вышел таймаут соединения если errno = None, иначе обрыв соединения.
                except OSError as err:
                    if err.errno:
                        CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                        break
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                    CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                    break
                # Если пакет корретно получен выводим в консоль и записываем в базу.
                else:
                    if ACTION in message and message[
                        ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                            and MESSAGE_TEXT in message and message[DESTINATION] == self.account_name:
                        print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                        # Захватываем работу с базой данных и сохраняем в неё сообщение
                        with database_lock:
                            try:
                                self.database.save_message(message[SENDER], self.account_name,
                                                           message[MESSAGE_TEXT])
                            except Exception as e:
                                CLIENT_LOGGER.error(f'Ошибка взаимодействия с базой данных {e}')

                        CLIENT_LOGGER.info(
                            f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    else:
                        CLIENT_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')

@log
def create_presence(account_name, password):
    """
    Функция генерирует запрос о присутствии клиента
    """
    out = {
        ACTION: PRESENCE,
        TIME: time.time(),
        CHAT_USER: {
            ACCOUNT_NAME: account_name
        },
        PASSWORD: password
    }
    CLIENT_LOGGER.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
    return out

@log
def process_response_ans(message):
    """
    Функция разбирает ответ сервера на сообщение о присутствии, возращает 200 если все ОК или\
    генерирует исключение при ошибке.
    """
    CLIENT_LOGGER.debug(f'Разбор приветственного сообщения от сервера: {message}')
    if RESPONSE in message:
        if message[RESPONSE] == 200:
            return '200 : OK'
        elif message[RESPONSE] == 400:
            CLIENT_LOGGER.critical(f'Ошибка сервера 400 : {message[ERROR]}')
    raise ValueError(RESPONSE)

@log
def arg_parser():
    """
    Парсер аргументов коммандной строки
    """
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=os.environ.get("DEFAULT_IP_ADDRESS"), nargs='?')
    parser.add_argument('port', default=os.environ.get("DEFAULT_PORT"), type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default=None, nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    password = namespace.password

    # проверим подходящий номер порта
    if not 1023 < server_port < 65536:
        CLIENT_LOGGER.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}. Допустимы адреса с 1024 до 65535. Клиент завершается.')
        exit(1)

    return server_address, server_port, client_name, password

def contacts_list_request(sock, name):
    """
    Функция, выполняющая запрос контакт-листа
    """
    CLIENT_LOGGER.debug(f'Запрос контакт листа для пользователся {name}')
    req = {
        ACTION: GET_CONTACTS,
        TIME: time.time(),
        CHAT_USER: name
    }
    CLIENT_LOGGER.debug(f'Сформирован запрос {req}')
    send_message(sock, req)
    ans = get_message(sock)
    CLIENT_LOGGER.debug(f'Получен ответ {ans}')
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        CLIENT_LOGGER.critical(f'Получен некорректный ответ на запрос контакт листа')
        sys.exit(1)

def add_contact(sock, username, contact):
    """
    Функция добавления пользователя в контакт лист
    """
    CLIENT_LOGGER.debug(f'Создание контакта {contact}')
    req = {
        ACTION: ADD_CONTACT,
        TIME: time.time(),
        CHAT_USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        CLIENT_LOGGER.critical(f'Получен некорректный ответ на запрос создания контакта')
        sys.exit(1)
    print('Удачное создание контакта.')

# Функция запроса списка известных пользователей
def user_list_request(sock, username):
    """
    Функция добавления пользователя в контакт лист
    """
    CLIENT_LOGGER.debug(f'Запрос списка известных пользователей {username}')
    req = {
        ACTION: USERS_REQUEST,
        TIME: time.time(),
        ACCOUNT_NAME: username
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 202:
        return ans[LIST_INFO]
    else:
        CLIENT_LOGGER.critical(f'Получен некорректный ответ на запрос списка известных пользователей')
        sys.exit(1)

def remove_contact(sock, username, contact):
    """
    Функция удаления пользователя из контакт листа
    """
    CLIENT_LOGGER.debug(f'Удаление контакта {contact}')
    req = {
        ACTION: DEL_CONTACT,
        TIME: time.time(),
        CHAT_USER: username,
        ACCOUNT_NAME: contact
    }
    send_message(sock, req)
    ans = get_message(sock)
    if RESPONSE in ans and ans[RESPONSE] == 200:
        pass
    else:
        CLIENT_LOGGER.critical(f'Получен некорректный ответ на запрос удаления контакта')
        sys.exit(1)
    print('Удачное удаление')

def database_load(sock, database, username):
    """
    Функция инициализатор базы данных. Запускается при запуске, загружает данные в базу с сервера.
    """
    # Загружаем список известных пользователей
    try:
        users_list = user_list_request(sock, username)
    except Exception as e:
        CLIENT_LOGGER.error(f'Ошибка запроса списка известных пользователей. {e}')
    else:
        database.add_users(users_list)

    # Загружаем список контактов
    try:
        contacts_list = contacts_list_request(sock, username)
    except Exception as e:
        CLIENT_LOGGER.error(f'Ошибка запроса списка контактов {e}')
    else:
        for contact in contacts_list:
            database.add_contact(contact)

def main():
    """
    Функия запуска клиентского приложения
    """
    # Сообщаем о запуске
    print('Консольный месседжер. Клиентский модуль.')

    # Загружаем параметы коммандной строки
    server_address, server_port, client_name, password = arg_parser()

    # Если имя пользователя не было задано, необходимо запросить пользователя.
    if not client_name:
        client_name = input('Введите имя пользователя: ')
    else:
        print(f'Клиентский модуль запущен с именем: {client_name}')

    if not password:
        password = input('Введите пароль: ')

    CLIENT_LOGGER.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , порт: {server_port}, имя пользователя: {client_name}')

    # Инициализация сокета и сообщение серверу о нашем появлении
    try:
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Таймаут 1 секунда, необходим для освобождения сокета.
        transport.settimeout(1)

        transport.connect((server_address, server_port))
        send_message(transport, create_presence(client_name, password))
        answer = process_response_ans(get_message(transport))
        CLIENT_LOGGER.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        print(f'Установлено соединение с сервером.')
    except Exception as e:
        CLIENT_LOGGER.error('Возникла ошибка при подключении к серверу')
        exit(1)
    else:

        # Инициализация БД
        database = ClientDatabase(client_name)
        database_load(transport, database, client_name)

        # Если соединение с сервером установлено корректно, запускаем поток взаимодействия с пользователем
        module_sender = ClientSender(client_name, transport, database)
        module_sender.daemon = True
        module_sender.start()
        CLIENT_LOGGER.debug('Запущены процессы')

        # затем запускаем поток - приёмник сообщений.
        module_receiver = ClientReader(client_name, transport, database)
        module_receiver.daemon = True
        module_receiver.start()

        # Watchdog основной цикл, если один из потоков завершён, то значит или потеряно соединение или пользователь
        # ввёл exit. Поскольку все события обработываются в потоках, достаточно просто завершить цикл.
        while True:
            time.sleep(1)
            if module_receiver.is_alive() and module_sender.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
