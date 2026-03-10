import re
from rest_framework import status
from rest_framework.exceptions import ValidationError

phone_regex = re.compile(r'^998(9[012345789]|6[125679]|7[01234569])[0-9]{7}$')
email_regex = re.compile(r'[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+')

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