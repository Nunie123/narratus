from flask import Flask
from flask_testing import TestCase
from backend.app.models import Connection
from backend.app import db
from backend.test import test_utils
from backend.app.encrypt import encrypt_with_aws, decrypt_with_aws


class UserModelTest(TestCase):

    def create_app(self):
        app = Flask(__name__)
        app.config.from_object(test_utils.Config())
        db.init_app(app)
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_dict_returns_dict(self):
        user = test_utils.create_user(username='samson')
        connection = Connection(label='con1', creator=user)
        db.session.add(connection)
        db.session.commit()

        connection_dict = connection.get_dict()

        assert isinstance(connection_dict, dict)
        assert connection_dict['connection_id']
        assert connection_dict['label'] == "con1"
        assert connection_dict['creator']['username'] == 'samson'

    def test_encrypt_output_different_from_password(self):
        plaintext = 'this test phrase'
        cipher_text = encrypt_with_aws(plaintext)

        assert plaintext != cipher_text

    def test_decrypt_output_matches_plaintext_input(self):
        plaintext = 'this test phrase'
        cipher_text = encrypt_with_aws(plaintext)
        output_text = decrypt_with_aws(cipher_text)

        assert plaintext == output_text

    def test_password_encrypt_and_decrypt(self):
        user = test_utils.create_user(username='samson')
        password = 'Secret123'
        connection = Connection(label='con1', creator=user, password=password)
        db.session.add(connection)
        db.session.commit()

        connection_dict = connection.get_dict()

        assert connection.password != password
        assert connection_dict['password'] == password
