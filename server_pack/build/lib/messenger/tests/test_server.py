import os
import unittest
from os.path import join, dirname
from dotenv import load_dotenv
from messenger.server import process_client_message


class TestServer(unittest.TestCase):
    def test_correct(self):
        self.assertEqual(process_client_message({
            os.environ.get("ACTION"): os.environ.get("PRESENCE"),
            os.environ.get("USER"): {os.environ.get("ACCOUNT_NAME"): 'Guest'}
        }), {os.environ.get("RESPONSE"): 200})

    def test_incorrect_user(self):
        self.assertEqual(process_client_message({
            os.environ.get("ACTION"): os.environ.get("PRESENCE"),
            os.environ.get("TIME"): 1.1,
            os.environ.get("USER"): {os.environ.get("ACCOUNT_NAME"): 'Some Other Guy'}
        }), {os.environ.get("RESPONSE"): 400, os.environ.get("ERROR"): 'Bad Request'})

    def test_no_user_mentioned(self):
        self.assertEqual(process_client_message({
            os.environ.get("ACTION"): os.environ.get("PRESENCE"),
            os.environ.get("TIME"): 1.1,
        }), {os.environ.get("RESPONSE"): 400, os.environ.get("ERROR"): 'Bad Request'})

    def test_unexpected_action(self):
        self.assertEqual(process_client_message({
            os.environ.get("ACTION"): 'Run',
            os.environ.get("TIME"): 1.1,
            os.environ.get("USER"): {os.environ.get("ACCOUNT_NAME"): 'Some Other Guy'}
        }), {os.environ.get("RESPONSE"): 400, os.environ.get("ERROR"): 'Bad Request'})


if __name__ == '__main__':
    dotenv_path = join(dirname(__file__), '../.env')
    load_dotenv(dotenv_path)
    unittest.main()
