

# takes list of usergroup objects, returns list of authorized user ids
def get_users_from_usergroups(usergroups):
    users_list_of_lists = list(map(lambda obj: obj.get_members(), usergroups))
    users = []
    list(map(users.extend, users_list_of_lists))   # this flattens the list of lists
    unique_users = list({user['user_id']:user for user in users}.values())
    return unique_users


# takes list of usergroup objects, returns list of usergroup dictionaries
def get_dicts_from_usergroups(usergroups):
    usergroup_list = list(map(lambda obj: obj.get_dict(), usergroups))
    return usergroup_list


def get_record_from_id(model, model_id):
    return model.query.filter(model.id == model_id).first()
