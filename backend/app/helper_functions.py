from backend.app import models


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
