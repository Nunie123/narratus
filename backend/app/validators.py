# Helper functions to validate input
import re
from app.models import User, Usergroup

# takes list of fields (as string)
# returns dict with results
def validate_required_fields(required_fields_list, provided_fields_dict):
    for field in required_fileds_list:
        if field not in provided_fields_dict:
            return {'validated':False, 'msg':'{} is required.'.format(field)}
    return {'validated':True}

def validate_user_exists(user_id):
    if not User.query.filter(User.id == user_id).first():
        msg = 'User not recognized.'
        return {'validated':False, 'msg':'{} is required.'.format(field)}
    return {'validated':True}

def validate_contact_exists(contact_id):
    if not Contact.query.filter(Contact.id == contact_id).first():
        msg = 'Contact not recognized.'
        return {'validated':False, 'msg':'{} is required.'.format(field)}
    return {'validated':True}

def validate_username(username):
    if not username:
        return {'validated':False, 'msg':'Username not provided.'}
    if User.query.filter(User.username == username).first():
        return {'validated':False, 'msg':'Username is not unique.'}
    if not re.match("^[a-zA-Z0-9]+$",username):
        return {'validated':False, 'msg':'Username can only contain numbers and letters.'}
    if 5 > len(username) or len(username) > 15:
        return {'validated':False, 'msg':'Username must be between 5 and 15 characters.'}
    return {'validated':True}

def validate_email(email):
    if not email:
        return {'validated':False, 'msg':'Email not provided.'}
    if not re.match("[^@]+@[^@]+\.[^@]+",email):
        return {'validated':False, 'msg':'Email is not in proper format.'}
    return {'validated':True}

def validate_password(password):
    if not password:
        return {'validated':False, 'msg':'Password not provided.'}
    if not re.match('\d.*[A-Z]|[A-Z].*\d', password):
        return {'validated':False, 'msg':'Password must contain one capital letter ane one number.'}
    if 8 > len(password) or len(password)> 50:
        return {'validated':False, 'msg':'Password must be between 8 and 50 characters.'}
    return {'validated':True}

def validate_role(role):
    if not role:
        return {'validated':False, 'msg':'Role not provided.'}
    if role not in ('viewer', 'writer', 'admin'):
        return {'validated':False, 'msg':'Invalid role type.'}
    return {'validated':True}

def validate_usergroup_ids(usergroup_ids):
    if len(usergroup_ids) == 0:
        return {'validated':False, 'msg':'At least one usergroup is required.'}
    for id in usergroup_ids:
        if not Usergroup.query.filter(Usergroup.id == id).first():
            return {'validated':False, 'msg':'Usergroup not recognized.'}
    return {'validated':True}
