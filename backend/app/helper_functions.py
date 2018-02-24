
# takes list of usergroup objects, returns list of authorized user ids
def get_users(usergroups):
    users_list_of_lists = list(map(lambda obj: obj.get_members(), usergroups))
    users = []
    list(map(users.extend, users_list_of_lists))   #this flattens the list of lists
    return set(users)

# takes list of usergroup objects, returns list of usergroup dictionaries
def get_usergroups(usergroups):
    usergroup_list = list(map(lambda obj: obj.get_dict(), usergroups))
    return usergroup_list
