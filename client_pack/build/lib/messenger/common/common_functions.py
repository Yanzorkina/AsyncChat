import os
import json
from os.path import join, dirname
from dotenv import load_dotenv


def get_message(client):
    """
    Функция принимающая сообщения от сервера
    """
    dotenv_path = join(dirname(__file__), '../.env')
    load_dotenv(dotenv_path)
    encoded_response = client.recv(int(os.environ.get("MAX_PACKAGE_LENGTH")))
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(os.environ.get("ENCODING"))
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        raise ValueError
    raise ValueError


def send_message(sock, message):
    """
    Функция посылающая сообщения на сервер
    """
    dotenv_path = join(dirname(__file__), '../.env')
    load_dotenv(dotenv_path)
    js_message = json.dumps(message)
    encoded_message = js_message.encode(os.environ.get("ENCODING"))
    sock.send(encoded_message)
