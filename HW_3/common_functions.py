import os
import json


def get_message(client):
    encoded_response = client.recv(int(os.environ.get("MAX_PACKAGE_LENGTH")))
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(os.environ.get("ENCODING"))
        response = json.loads(json_response)
        if isinstance(response, dict):
            return response
        raise ValueError
    raise ValueError


def send_message(sock, message):
    js_message = json.dumps(message)
    encoded_message = js_message.encode(os.environ.get("ENCODING"))
    sock.send(encoded_message)
