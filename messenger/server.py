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
from metaclass_server import ServerMaker

SERVER_LOGGER = LOGGER

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


class Server(metaclass=ServerMaker):
    port = Port()

    def __init__(self, listen_address, listen_port):
        self.addr = listen_address
        self.port = listen_port
        # очередь клиентов, сообщений, словарь сопоставления сокета и имени
        self.clients = []
        self.messages = []
        self.names = {}

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

            try:
                if self.clients:
                    recv_data_list, send_data_list, error_list = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            # Прием сообщений
            if recv_data_list:
                for client_with_message in recv_data_list:
                    try:
                        self.process_client_message(get_message(client_with_message), client_with_message)
                    except Exception as e:
                        # print(e, 'строка 97')  # какая ошибка
                        SERVER_LOGGER.info(f'{client_with_message.getpeername()} отключился.')
                        self.clients.remove(client_with_message)

            # Обработка сообщений
            for message in self.messages:
                try:
                    self.process_message(message, send_data_list)
                except Exception:
                    SERVER_LOGGER.info(f'Связь с {message[os.environ.get("DESTINATION")]} была потеряна')
                    self.clients.remove(self.names[message[os.environ.get("DESTINATION")]])
                    del self.names[message[os.environ.get("DESTINATION")]]
            self.messages.clear()

    @log
    def process_message(self, message, listen_socks):
        if message[os.environ.get("DESTINATION")] in self.names and self.names[
            message[os.environ.get("DESTINATION")]] in listen_socks:
            send_message(self.names[message[os.environ.get("DESTINATION")]], message)
            LOGGER.info(f'Отправлено сообщение пользователю {message[os.environ.get("DESTINATION")]} '
                        f'от пользователя {message[os.environ.get("SENDER")]}.')
        elif message[os.environ.get("DESTINATION")] in self.names and self.names[
            message[os.environ.get("DESTINATION")]] not in listen_socks:
            raise ConnectionError
        else:
            LOGGER.error(
                f'Пользователь {message[os.environ.get("DESTINATION")]} не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')

    @log
    def process_client_message(self, message, client):
        SERVER_LOGGER.debug(f'Получено сообщение от клиента: {message}')
        # Для сообщение о присутствии.
        if os.environ.get("ACTION") in message and message[os.environ.get("ACTION")] == os.environ.get(
                "PRESENCE") and os.environ.get("TIME") in message and os.environ.get("CHAT_USER") in message:
            # Пользователь не зарегестрирован
            if message[os.environ.get("CHAT_USER")][os.environ.get("ACCOUNT_NAME")] not in self.names.keys():
                self.names[message[os.environ.get("CHAT_USER")][os.environ.get("ACCOUNT_NAME")]] = client
                send_message(client, {os.environ.get("RESPONSE"): 200})
                print(f"Зарегистрирован пользователь {client}")
            else:
                response = {os.environ.get("RESPONSE"): 400, os.environ.get("ERROR"): None}
                response[os.environ.get("ERROR")] = 'Это имя уже занято'
                send_message(client, response)
                self.clients.remove(client)
                client.close()
            return
        # Для сообщений с содержимым
        elif os.environ.get("ACTION") in message and message[os.environ.get("ACTION")] == os.environ.get(
                "MESSAGE") and os.environ.get("DESTINATION") in message and os.environ.get(
            "TIME") in message and os.environ.get("SENDER") in message and os.environ.get("MESSAGE_TEXT") in message:
            self.messages.append(message)
            return
        # Если клиент выходит
        elif os.environ.get("ACTION") in message and message[os.environ.get("ACTION")] == os.environ.get(
                "EXIT") and os.environ.get("ACCOUNT_NAME") in message:
            self.clients.remove(self.names[message[os.environ.get("ACCOUNT_NAME")]])
            self.names[message[os.environ.get("ACCOUNT_NAME")]].close()
            del self.names[message[os.environ.get("ACCOUNT_NAME")]]
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

    server = Server(listen_address, listen_port)
    server.main_loop()


if __name__ == '__main__':
    main()
