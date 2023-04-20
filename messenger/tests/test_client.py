import os
import unittest
from os.path import join, dirname
from dotenv import load_dotenv
from messenger.client import create_presence, process_ans


class TestClass(unittest.TestCase):

    def test_status_200(self):
        self.assertEqual(process_ans({os.environ.get("RESPONSE"): 200}), '200 : OK')

    def test_status_400(self):
        self.assertEqual(process_ans({os.environ.get("RESPONSE"): 400, os.environ.get("ERROR"): "Bad Request"}),
                         '400 : Bad Request')

    def test_create_presence(self):
        test = create_presence()
        test[os.environ.get("TIME")] = 1.1
        self.assertEqual(test, {os.environ.get("ACTION"): os.environ.get("PRESENCE"),
                                os.environ.get("TIME"): 1.1, os.environ.get("USER"): {
                os.environ.get("ACCOUNT_NAME"): 'Guest'}})


if __name__ == '__main__':
    dotenv_path = join(dirname(__file__), '../.env')
    load_dotenv(dotenv_path)
    unittest.main()
