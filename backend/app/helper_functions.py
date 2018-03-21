from backend.app import models
from backend.app import db


# takes list of usergroup objects, returns list of authorized user ids
def get_users_from_usergroups(usergroups):
    users_list_of_lists = list(map(lambda obj: obj.get_members(), usergroups))
    users = []
    list(map(users.extend, users_list_of_lists))   # this flattens the list of lists
    unique_users = list({user['user_id']: user for user in users}.values())
    return unique_users


# takes list of usergroup objects, returns list of usergroup dictionaries
def get_dicts_from_usergroups(usergroups):
    usergroup_list = list(map(lambda obj: obj.get_dict(), usergroups))
    return usergroup_list


def get_record_from_id(model, model_id):
    return model.query.filter(model.id == model_id).first()


def get_personal_usergroup_from_user_object(user):
    usergroup = models.Usergroup.query.filter(models.Usergroup.label == 'personal_{}'.format(user.username)).first()
    return usergroup


def get_user_from_username(username):
    return models.User.query.filter(models.User.username == username).first()


def any_args_are_truthy(*args):
    for arg in args:
        if arg:
            return True
    return False


def requester_has_admin_privileges(requester):
    return requester['role'] in ['admin', 'superuser']


def requester_has_write_privileges(requester):
    return requester['role'] in ['writer', 'admin', 'superuser']


def create_user_from_dict(user_dict):
    user = models.User(username=user_dict.get('username', None)
                       , role=user_dict.get('role', None)
                       , is_active=user_dict.get('is_active', None)
                       , email=user_dict.get('email', None)
                       )

    user.set_password(user_dict['password'])
    for usergroup_id in user_dict['usergroup_ids']:
        usergroup = get_record_from_id(models.Usergroup, usergroup_id)
        if not usergroup:
            raise AssertionError('Usergroup_id {} not recognized'.format(usergroup_id))
        user.usergroups.append(usergroup)

    usergroup = create_personal_usergroup_from_dict(user_dict)
    user.usergroups.append(usergroup)

    db.session.add(user)
    db.session.commit()
    return user


def create_personal_usergroup_from_dict(user_dict):
    usergroup_label = user_dict['username']
    usergroup = models.Usergroup(label=usergroup_label, personal_group=True)
    db.session.add(usergroup)
    db.session.commit()

    return usergroup
