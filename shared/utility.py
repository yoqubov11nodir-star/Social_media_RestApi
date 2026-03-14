import re
from rest_framework import status
from rest_framework.exceptions import ValidationError

phone_regex = re.compile(r'^998(9[012345789]|6[125679]|7[01234569])[0-9]{7}$')
email_regex = re.compile(r'[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+')
username_regex = re.compile(r'^[a-z0-9_-]{3,15}$')

def check_email_or_phone(user_input):
    if re.fullmatch(phone_regex, user_input):
        data = 'phone'
    elif re.fullmatch(email_regex, user_input):
        data = 'email'
    else:
        response = {
            'message': 'Email yoki telefon raqam xato kiritilgan'
        }
        raise ValidationError(response)
    
    return data

def check_email_or_phone_or_username(user_input):
    if re.fullmatch(phone_regex, user_input):
        data = 'phone'
    elif re.fullmatch(email_regex, user_input):
        data = 'email'

    elif re.fullmatch(username_regex, user_input):
        return 'username'
    else:
        response = {
            'message': 'Login xato kiritilgan'
        }
        raise ValidationError(response)
    
    return data