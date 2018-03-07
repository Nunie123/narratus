import json
from backend.app import db
from backend.app.models import User, Usergroup


class Config:
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class TestUtils:

    def create_user_and_login(self, username='sam', password='Secret123', role='admin'):
        self.create_user(username=username, password=password, role=role)
        return self.login(username=username, password=password, role=role)

    def login(self, username='sam', password='Secret123', role='admin'):
        data = dict(username=username, password=password, role=role)
        return self.client.post('/api/login', data=json.dumps(data), content_type='application/json')

    def logout(self, token):
        return self.client.post('/api/logout', headers={'Authorization': 'Bearer {}'.format(token)})

    def create_user(self, username: str = 'samson', password: str = 'Secret123', email: str = 'sseaborn@whitehouse.gov'
                    , role: str = 'admin', user_id: int = None, usergroup_label: str = 'ug1') -> User:
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        if user_id:
            user.id = user_id
        usergroup = Usergroup.query.filter(Usergroup.label == usergroup_label).first()
        if not usergroup:
            usergroup = self.create_usergroup(label=usergroup_label)
        personal_usergroup = Usergroup(label='personal_{}'.format(username))
        user.usergroups.append(usergroup)
        user.usergroups.append(personal_usergroup)
        db.session.add(usergroup)
        db.session.add(personal_usergroup)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def create_usergroup(label: str = 'usergroup1', usergroup_id=None):
        usergroup = Usergroup(label=label)
        if usergroup_id:
            usergroup.id = usergroup_id
        db.session.add(usergroup)
        db.session.commit()
        return usergroup

    @staticmethod
    def get_number_of_users():
        return len(User.query.all())
