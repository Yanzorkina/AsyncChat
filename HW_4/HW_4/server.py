import os
import socket
import sys
import json
from os.path import join, dirname
from dotenv import load_dotenv
from common_functions import get_message, send_message


def process_client_message(message):
    if not (not (os.environ.get("ACTION") in message) or not (message[os.environ.get("ACTION")] == os.environ.get(
            "PRESENCE")) or not (os.environ.get("TIME") in message) or not (os.environ.get("USER") in message) or not (
            message[os.environ.get("USER")][os.environ.get("ACCOUNT_NAME")] == 'Guest')):
        return {os.environ.get("RESPONSE"): 200}
    return {
        os.environ.get("RESPONSE"): 400,
        os.environ.get("ERROR"): 'Bad Request'
    }


def main():
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            listen_port = os.environ.get("DEFAULT_PORT")
        if int(listen_port) < 1024 or int(listen_port) > 65535:
            raise ValueError
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
        else:
            listen_address = ''

    except IndexError:
        print(
            'В случае указания параметра \'a\'- необходимо указать адрес.')
        sys.exit(1)

    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    transport.bind((listen_address, int(listen_port)))

    transport.listen(int(os.environ.get("MAX_CONNECTIONS")))

    while True:
        client, client_address = transport.accept()
        try:
            message_from_client = get_message(client)
            print(message_from_client)
            response = process_client_message(message_from_client)
            send_message(client, response)
            client.close()
        except (ValueError, json.JSONDecodeError):
            print('Принято некорретное сообщение от клиента.')
            client.close()


if __name__ == '__main__':
    main()
