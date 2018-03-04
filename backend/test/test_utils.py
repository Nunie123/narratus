import json
from flask import Flask
from app import db, routes, app
from app.models import (
    User
)

class Config:
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestUtils:

    def create_user_and_login(self, username='sam', password='secret', role='admin'):
        self.create_user(username=username, password=password, role=role)
        return self.login(username=username, password=password, role=role)

    def login(self, username='sam', password='secret', role='admin'):
        data = dict(username=username, password=password, role=role)
        return self.client.post('/api/login', data=json.dumps(data), content_type='application/json')

    def logout(self, token):
        return self.client.post('/api/logout', headers={'Authorization': 'Bearer {}'.format(token)})

    def create_user(self, username='sam', password='secret', email='sseaborn@whitehouse.gov', role='admin', user_id=None):
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        if user_id:
            user.id = user_id
        db.session.add(user)
        db.session.commit()
        return user
