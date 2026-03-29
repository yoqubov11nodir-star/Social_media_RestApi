from rest_framework import serializers, status
from .models import CodeVerifiy, CustomUser, VIA_EMAIL, VIA_PHONE, CODE_VERIFIY, DONE, PHOTO_DONE, Post, Comment, Like, Follow, Story, CustomUser
from rest_framework.exceptions import ValidationError
from shared.utility import check_email_or_phone, check_email_or_phone_or_username
from django.db.models import Q
from django.core.mail import send_mail
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.mail import send_mail
from .models import CustomUser, VIA_EMAIL, VIA_PHONE
from shared.utility import check_email_or_phone

class SignupSerialzier(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    auth_status = serializers.CharField(read_only=True)
    auth_type = serializers.CharField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email_or_phone'] = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'auth_status', 'auth_type']

    def validate(self, attrs):
        user_input = attrs.get('email_or_phone')
        SignupSerialzier.auth_validate(user_input)
        return attrs

    def create(self, validated_data):
        user_input = validated_data.get('email_or_phone')
        data = self.auth_validate(user_input)
        
        data['username'] = user_input
        
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

        return user

    @staticmethod
    def auth_validate(user_input):
        user_input_type = check_email_or_phone(user_input)
        if user_input_type == 'phone':
            return {'auth_type': VIA_PHONE, 'phone_number': user_input}
        elif user_input_type == 'email':
            return {'auth_type': VIA_EMAIL, 'email': user_input}
        raise ValidationError({
            "success": False,
            "message": "Email yoki telefon raqami noto'g'ri."
        })
    
    
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
        instance.set_password(validated_data.get('password'))

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
            instance.auth_status = PHOTO_DONE
        instance.save()

        return instance
    

class LoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_input'] = serializers.CharField(required=True, write_only=True)
        self.fields['password'] = serializers.CharField(required=True, write_only=True)
        if 'username' in self.fields:
            self.fields['username'].required = False

    def validate(self, attrs):
        user = self.check_user_type(attrs)
        full_token = user.token()
        return {
            'status': status.HTTP_200_OK,
            'message': "Siz tizimga kirdingiz",
            'access': full_token['access'],
            'refresh': full_token['refresh'],
            'username': user.username
        }

    def check_user_type(self, data):
        user_input = data.get('user_input')
        password = data.get('password')
        user_type = check_email_or_phone_or_username(user_input)

        if user_type == 'username':
            user = CustomUser.objects.filter(username=user_input).first()
        elif user_type == 'email':
            user = CustomUser.objects.filter(email__iexact=user_input).first()
        elif user_type == 'phone':
            user = CustomUser.objects.filter(phone_number=user_input).first()
        else:
            raise ValidationError("Ma'lumot topilmadi")

        if not user:
            raise ValidationError({"message": "Login xato kiritildi", "status": status.HTTP_400_BAD_REQUEST})

        if user.auth_status not in [DONE, PHOTO_DONE]:
            raise ValidationError("Siz hali to'liq ro'yxatdan o'tmadingiz")

        authenticated_user = authenticate(username=user.username, password=password)

        if not authenticated_user:
            raise ValidationError("Parol xato")

        return authenticated_user
    

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
    
    
class PostSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.username', read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()


    class Meta:
        model = Post
        fields = ['id', 'author', 'title', 'desc', 'image', 'likes_count', 'comments_count', 'created_at']

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.username', read_only=True)
    replies = serializers.SerializerMethodField()


    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'text', 'parent', 'replies', 'created_at']

    def get_replies(self, obj):
        if obj.replies.exists():
            return CommentSerializer(obj.replies.all(), many=True).data
        return []


class LikeSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.username', read_only=True)


    class Meta:
        model = Like
        fields = ['id', 'user', 'post', 'comment']

    def validate(self, attrs):
        post = attrs.get('post')
        comment = attrs.get('comment')
        
        if post and comment:
            raise serializers.ValidationError("Faqat bitta obyektga (Post yoki Comment) like bosa olasiz")
        if not post and not comment:
            raise serializers.ValidationError("Like bosish uchun Post yoki Comment tanlang.")
        
        return attrs


class FollowSerializer(serializers.ModelSerializer):
    follower = serializers.CharField(source='follower.username', read_only=True)
    following_name = serializers.CharField(source='following.username', read_only=True)


    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'following_name', 'created_at']


class StorySerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Story
        fields = ['id', 'author', 'image', 'video', 'text', 'expiration_time', 'created_at']
        extra_kwargs = {'expiration_time': {'required': False}}


class ProfileSerializer(serializers.ModelSerializer):
    posts_count = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'first_name', 'last_name', 
            'email', 'phone_number', 'photo', 'user_role',
            'posts_count', 'followers_count', 'following_count'
        ]

    def get_posts_count(self, obj):
        return obj.posts.count()

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()
    