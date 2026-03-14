from rest_framework import serializers, status
from .models import CodeVerifiy, CustomUser, VIA_EMAIL, VIA_PHONE, CODE_VERIFIY, DONE, PHOTO_DONE
from rest_framework.exceptions import ValidationError
from shared.utility import check_email_or_phone, check_email_or_phone_or_username
from django.db.models import Q
from django.core.mail import send_mail
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

class SignupSerialzier(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    auth_status = serializers.CharField(read_only=True)
    auth_type = serializers.CharField(read_only=True)

    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
        self.fields['email_or_phone'] = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'auth_status', 'auth_type']

    def create(self, validated_data):
      
        user_input = self.context['request'].data.get('email_or_phone')
        data = self.auth_validate(user_input)
        
        user = CustomUser.objects.create_user(**data)
        
        if user.auth_type == VIA_EMAIL:
            code = user.generate_code(VIA_EMAIL)
            send_mail(
                subject="Tasdiqlash kodi",
                message=f"Sizning tasdiqlash kodingiz: {code}",
                from_email="yoqubov11nodir@gmail.com",
                recipient_list=[user.email],
                fail_silently=False,
            )
        elif user.auth_type == VIA_PHONE:
            code = user.generate_code(VIA_PHONE)
            print(f"SMS code for {user.phone_number}: {code}")

        user.save()
        return user

    def validate(self, attrs):
        user_input = self.context['request'].data.get('email_or_phone')
        self.auth_validate(user_input)
        self.validate_email_or_phone(user_input)
        return attrs

    @staticmethod
    def auth_validate(data):
        user_input = data.get('email_or_phone')
        user_input_type = check_email_or_phone(user_input)
        if user_input_type == 'phone':
            return {'auth_type': VIA_PHONE, 'phone_number': user_input}
        elif user_input_type == 'email':
            return {'auth_type': VIA_EMAIL, 'email': user_input}
        return None

    def validate_email_or_phone(self, email_or_phone):
        if CustomUser.objects.filter(Q(phone_number=email_or_phone) | Q(email=email_or_phone)).exists():
            raise ValidationError(detail="Bu email yoki telefon raqam bilan oldin ro'yxatdan o'tilgan.")
        return email_or_phone
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['message'] = 'Kodingiz yuborildi'
        data['refresh'] = instance.token()['refresh']
        data['access'] = instance.token()['access']
        return data
    
class UserChangeInfoSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        return attrs
    
    def validate_username(self, value):
        if not value.isalnum() and '_' not in value:
            raise ValidationError("Username faqat harf, raqam va pastki chiziqdan iborat bo'lishi kerak.")
        
        if len(value) < 5:
            raise ValidationError("Username kamida 5 ta belgidan iborat bo'lishi kerak.")

        if CustomUser.objects.filter(username=value).exists():
            raise ValidationError("Bu username band. Iltimos, boshqasini tanlang.")
        
        return value

    def validate_first_name(self, value):
        if any(char.isdigit() for char in value):
            raise ValidationError("Ismda raqamlar ishlatilishi mumkin emas.")
        
        return value.strip()

    def validate_last_name(self, value):
        if any(char.isdigit() for char in value):
            raise ValidationError("Familiyada raqamlar ishlatilishi mumkin emas.")
        
        return value.strip()

    def update(self, instance, validated_data):
        if instance.auth_status != CODE_VERIFIY:
            raise ValidationError({"message": "Siz hali tasdiqlanmagansiz", "status": status.HTTP_400_BAD_REQUEST})
        
        instance.first_name = validated_data.get('first_name')
        instance.last_name = validated_data.get('last_name')
        instance.username = validated_data.get('username')
        instance.password.set_password(validated_data.get('password'))

        instance.auth_status = DONE
        instance.save()

        return instance
    
class PhotoStatusSerializer(serializers.Serializer):
    photo = serializers.ImageField()

    def update(self, instance, validated_data):
        photo = validated_data.get('photo', None)
        if photo:
            instance.photo = photo
        if instance.auth_status == DONE:
            instance.auth_status == PHOTO_DONE
        instance.save()

        return instance
    
class LoginSerializer(TokenObtainPairSerializer):
    password = serializers.CharField(required=True, write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_input'] = serializers.CharField(required=True, write_only=True)
        self.field['username'] = serializers.CharField(read_only=True)

    def validate(self, attrs):
        user = self.check_user_type(attrs)
        response_data = {
            'status': status.HTTP_200_OK,
            'meassage': "Siz tizimga kirdingiz",
            'access': user.token()['access'],
            'refresh': user.token()['refresh']
        }
        return response_data

    def check_user_type(self, data):
        password = data.get('password')
        user_input_data = data.get('user_input')
        user_type = check_email_or_phone_or_username(data.get('user_input'))
        if user_type == 'username':
            user = CustomUser.objects.filter(username=user_input_data).first()
            self.get_object(user)
            username = user_input_data
        elif user_type == 'email':
            user = CustomUser.objects.filter(email__icontains=user_input_data.lower()).first()
            self.get_object(user)
            username = user.username

        elif user_type == 'phone':
            user = CustomUser.objects.filter(phone_number=user_input_data).first()
            self.get_object(user)
        else:
            raise ValidationError(detail="Ma'lumot topilmadi")
        
        authentication_kwargs = {
            "password": password,
            self.username_field: username
            }
        
        if user.auth_stauts in [DONE, PHOTO_DONE]:
            raise ValidationError(detail="Siz hali to'liq ro'yhatdan o'tmadingiz")

        user = authenticate(**authentication_kwargs)

        if not user:
            raise ValidationError('Parol xato')
        
        return user

    def get_object(self, user):
        if not user:
            raise ValidationError({"meassage": "Login xato kiritdingiz", 'status': status.HTTP_400_BAD_REQUEST})
        
        return True
    
class ForgotPasswordSerializer(serializers.Serializer):
    user_input = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        user_data = attrs.get('user_input')
        user = CustomUser.objects.filter(Q(username=user_data) | Q(email=user_data) | Q(phone_number=user_data)).first()

        if not user:
            raise ValidationError("Foydalanuvchi topilmadi.")

        if user.email:
            code = user.generate_code(VIA_EMAIL)
            send_mail(
                subject="Parolni tiklash",
                message=f"Sizning tiklash kodingiz: {code}",
                from_email="yoqubov11nodir@gmail.com",
                recipient_list=[user.email],
            )
        elif user.phone_number:
            code = user.generate_code(VIA_PHONE)
            print(f"SMS code for {user.phone_number}: {code}")
        
        return attrs

class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('confirm_password'):
            raise ValidationError("Parollar bir-biriga mos kelmadi.")
        return attrs

    def update(self, instance, validated_data):
        instance.set_password(validated_data.get('password'))
        instance.save()
        return instance