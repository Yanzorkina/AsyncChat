import os
import unittest
import json
from os.path import join, dirname
from dotenv import load_dotenv
from messenger.common_functions import send_message, get_message


class TestSocket:
    def __init__(self, test_dict):
        self.test_dict = test_dict
        self.encoded_message = None
        self.received_message = None

    def send(self, message_to_send):
        json_test_message = json.dumps(self.test_dict)
        self.encoded_message = json_test_message.encode(os.environ.get("ENCODING"))
        self.received_message = message_to_send

    def recv(self, max_len):
        json_test_message = json.dumps(self.test_dict)
        return json_test_message.encode(os.environ.get("ENCODING"))


class TestClass(unittest.TestCase):
    test_dict_send = {
        os.environ.get('ACTION'): os.environ.get('PRESENCE'),
        os.environ.get('TIME'): 1.1,
        os.environ.get('USER'): {
            os.environ.get('ACCOUNT_NAME'): 'test_test'
        }
    }
    test_dict_recv_ok = {'null': 200}
    test_dict_recv_err = {
        'null': 'Bad Request'
    }

    def test_send_message(self):
        test_socket = TestSocket(self.test_dict_send)
        send_message(test_socket, self.test_dict_send)
        self.assertEqual(test_socket.encoded_message, test_socket.received_message)
        with self.assertRaises(Exception):
            send_message(test_socket, test_socket)

    def test_get_message(self):
        test_sock_ok = TestSocket(self.test_dict_recv_ok)
        test_sock_err = TestSocket(self.test_dict_recv_err)
        self.assertEqual(get_message(test_sock_ok), self.test_dict_recv_ok)
        self.assertEqual(get_message(test_sock_err), self.test_dict_recv_err)


if __name__ == '__main__':
    dotenv_path = join(dirname(__file__), '../.env')
    load_dotenv(dotenv_path)
    unittest.main()
