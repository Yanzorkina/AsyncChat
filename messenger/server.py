import os
import select
import socket
import sys
import threading
from os.path import join, dirname
from dotenv import load_dotenv
from common.common_functions import get_message, send_message
from log.server_log_config import LOGGER
from chatapp.common.wrap import log
from chatapp.common.metaclass_server import ServerMaker
from chatapp.database.storage import ServerStorage

from common.jim_variables import *

SERVER_LOGGER = LOGGER
new_connection = False
conflag_lock = threading.Lock()


# Дескриптор порта
class Port:
    def __set__(self, instance, value):
        if not 1023 < int(value) < 65536:
            SERVER_LOGGER.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {value}. Допустимы адреса с 1024 до 65535.')
            exit(1)
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class Server(threading.Thread, metaclass=ServerMaker):
    port = Port()

    def __init__(self, listen_address, listen_port, database):
        self.addr = listen_address
        self.port = listen_port
        # очередь клиентов, сообщений, словарь сопоставления сокета и имени
        self.clients = []
        self.messages = []
        self.names = {}
        self.database = database

        super().__init__()

    def init_socket(self):
        # Подготовка сокета
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind((self.addr, int(self.port)))
        transport.settimeout(0.5)

        # Прослушивание порта
        self.sock = transport
        self.sock.listen(int(os.environ.get("MAX_CONNECTIONS")))

    def main_loop(self):
        self.init_socket()
        # Главный цикл программы.
        while True:
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOGGER.info(f'Соединение {client_address} с установлено')
                self.clients.append(client)

            # Списки клиентов в очереди
            recv_data_list = []
            send_data_list = []
            error_list = []

            # Есть ли клиенты в состоянии ожидания
            try:
                if self.clients:
                    recv_data_list, send_data_list, error_list = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            # Прием сообщений.
            if recv_data_list:
                for client_with_message in recv_data_list:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except Exception as e:
                        print(e, 'строка 88')  # какая ошибка
                        SERVER_LOGGER.info(f'{client_with_message.getpeername()} отключился.')
                        self.clients.remove(client_with_message)

            # Обработка сообщений
            for message in self.messages:
                try:
                    self.process_message(message, send_data_list)
                except Exception:
                    SERVER_LOGGER.info(f'Связь с {message[DESTINATION]} была потеряна')
                    self.clients.remove(self.names[message[DESTINATION]])
                    del self.names[message[DESTINATION]]
            self.messages.clear()

    @log
    def process_message(self, message, listen_socks):
        if message[DESTINATION] in self.names and self.names[
            message[DESTINATION]] in listen_socks:
            send_message(self.names[message[DESTINATION]], message)
            SERVER_LOGGER.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                               f'от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in self.names and self.names[
            message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            SERVER_LOGGER.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')

    @log
    def process_client_message(self, message, client):
        global new_connection
        SERVER_LOGGER.debug(f'Получено сообщение от клиента: {message}')
        # Для сообщение о присутствии.
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and CHAT_USER in message:
            # Пользователь не зарегестрирован
            if message[CHAT_USER][ACCOUNT_NAME] not in self.names.keys():
                self.names[message[CHAT_USER][ACCOUNT_NAME]] = client
                send_message(client, {RESPONSE: 200})
                client_ip = client.getpeername()[0]
                try:
                    self.database.user_login(message[CHAT_USER][ACCOUNT_NAME], client_ip)
                    print(f"В базе данных зарегистрирован пользователь {client}")
                except Exception as err:
                    print(err)
                    print(f'Пользователь {client} уже зарегестрирован в базе данных')
                with conflag_lock:
                    new_connection = True
            # Пользователь зарегестрирован
            else:
                response = {RESPONSE: 400, ERROR: None}
                response[ERROR] = 'Это имя уже занято'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Для сообщений с содержимым
        elif ACTION in message and message[
            ACTION] == MESSAGE and DESTINATION in message and TIME in message and SENDER in message and MESSAGE_TEXT in message:
            self.messages.append(message)
            return
        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.clients.remove(self.names[message[ACCOUNT_NAME]])
            self.names[message[ACCOUNT_NAME]].close()
            del self.names[message[ACCOUNT_NAME]]
            with conflag_lock:
                new_connection = True
            return
        # Блок обработки запросов, савязанных со списком контактов.
        # Запрос списка контактов
        elif ACTION in message and message[ACTION] == GET_CONTACTS and CHAT_USER in message and self.names[
            message[CHAT_USER]] == client:
            response = {RESPONSE: 202,
                        ALERT: self.database.get_contacts(message[CHAT_USER])}
            send_message(client, response)
        # Запрос добавления контакта
        elif ACTION in message and message[ACTION] == ADD_CONTACT and CHAT_USER in message and message[TARGET_USER]:
            response = {RESPONSE: 200}
            self.database.add_contact(message[CHAT_USER], message[TARGET_USER])
            self.message = send_message(client, response)
        # Запрос удаления контакта
        elif ACTION in message and message[ACTION] == DEL_CONTACT and CHAT_USER in message and self.names[message[
            CHAT_USER]] == client and TARGET_USER in message:
            response = {RESPONSE: 200, ALERT: f"Пользователь {message[TARGET_USER]} удален из списка контактов"}

            try:
                self.database.del_contact(message[CHAT_USER], message[TARGET_USER])
                send_message(client, response)
            except:
                print("Не удалось удалить пользователя")


        # Иначе отдаём Bad request
        else:
            response = {RESPONSE: 400, ERROR: None}
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return


def main():
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    database = ServerStorage()

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

    server = Server(listen_address, listen_port, database)
    server.main_loop()


if __name__ == '__main__':
    main()
