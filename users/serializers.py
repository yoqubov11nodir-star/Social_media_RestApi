from rest_framework import serializers, status
from .models import CodeVerifiy, CustomUser, VIA_EMAIL, VIA_PHONE
from rest_framework.exceptions import ValidationError
from shared.utility import check_email_or_phone

class SignupSerialzier(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True, required=True)
    auth_status = serializers.CharField(read_only=True, required=True)
    verify_type = serializers.CharField(read_only=True, required=True)

    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
        super.fields['email_or_phone'] = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'auth_status', 'verify_type']

    @staticmethod
    def auth_validate(user_input):
        user_input_type = check_email_or_phone(user_input)
        if user_input_type == 'phone':
            data = {
                'verify_type': VIA_PHONE,
                'phone': user_input
            }
        elif user_input_type == 'email':
            data = {
                'verify_type': VIA_EMAIL,
                'email': user_input
            }
        else:
            response = {
            'status': status.HTTP_400_BAD_REQUEST,
            'message': 'Email yoki telefon raqam xato kiritilgan',
            }
            raise ValidationError(response)
        return data