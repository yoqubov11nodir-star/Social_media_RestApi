from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from shared.models import BaseModel
from datetime import datetime, timedelta
from config.settings import EMAIL_EXPIRATION_TIME, PHONE_EXPIRATION_TIME
from rest_framework_simplejwt.tokens import RefreshToken
import uuid
import random

ORDINARY_USER, ADMIN, MANAGER = ('ordinary_user', 'admin', 'manager')
NEW, CODE_VERIFIY, DONE, PHOTO_DONE, POST, PROFILE, COMMENT, LIKE, FOLLOW, STORY = ('new', 'code_verifiy', 'done', 'photo_done', 
'post', 'profile', 'comment', 'like', 'follow', 'story')
VIA_EMAIL, VIA_PHONE = ('via_email', 'via_phone')

class CustomUser(AbstractUser, BaseModel):
    USER_ROLE = (
        (ORDINARY_USER, ORDINARY_USER),
        (ADMIN, ADMIN),
        (MANAGER, MANAGER),
    )
    USER_AUTH_STATUS = (
        (NEW, NEW),
        (CODE_VERIFIY, CODE_VERIFIY),
        (DONE, DONE),
        (PHOTO_DONE, PHOTO_DONE),
        (POST, POST),
        (PROFILE, PROFILE),
        (COMMENT, COMMENT),
        (LIKE, LIKE),
        (FOLLOW, FOLLOW),
        (STORY, STORY)
    )
    USER_AUTH_TYPE = (
        (VIA_EMAIL, VIA_EMAIL),
        (VIA_PHONE, VIA_PHONE)
    )

    user_role = models.CharField(max_length=20, choices=USER_ROLE, default=ORDINARY_USER)
    auth_status = models.CharField(max_length=20, choices=USER_AUTH_STATUS, default=NEW)
    auth_type = models.CharField(max_length=20, choices=USER_AUTH_TYPE)
    email = models.EmailField(max_length=50, blank=True, null=True, unique=True)
    phone_number = models.CharField(max_length=13, blank=True, null=True, unique=True)
    photo = models.ImageField(upload_to='user_photos/', validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'heic'])])

    def __str__(self):
        return self.username

    def check_username(self):
        if not self.username:
            temp_username = f"username{uuid.uuid4().hex[:8]}"
            while CustomUser.objects.filter(username=temp_username).exists():
                temp_username = f"username{uuid.uuid4().hex[:8]}{random.randint(0, 9)}"
            self.username = temp_username

    def check_pass(self):
        if not self.password:
            temp_password = f"pass{uuid.uuid4().hex[:8]}"
            self.password = temp_password

    def hashing_pass(self):
        if self.password and not self.password.startswith(('pbkdf2_sha256$', 'argon2$', 'bcrypt')):
            self.set_password(self.password)

    def check_email(self):
        if self.email:
            self.email = self.email.lower()

    def token(self):
        refresh_token = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh_token),
            'access': str(refresh_token.access_token)
        }
    
    def generate_code(self, verify_type):
        from .models import CodeVerifiy 

        code = random.randint(1000, 9999)
        CodeVerifiy.objects.create(
            code=code,
            user=self,
            verify_type=verify_type
        )
        return code

    def clean(self):
        self.check_email()
        self.check_username()
        self.check_pass()
        self.hashing_pass()
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class CodeVerifiy(BaseModel):
    VERIFIY_TYPE = (
        (VIA_EMAIL, VIA_EMAIL),
        (VIA_PHONE, VIA_PHONE)
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='verify_codes')
    code = models.CharField(max_length=4)
    verifiy_type = models.CharField(max_length=30, choices=VERIFIY_TYPE)
    expiration_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)

    def save(self, *arg, **kwargs):
        if  self.verifiy_type == VIA_EMAIL:
            self.expiration_time = datetime.now() + timedelta(minutes=EMAIL_EXPIRATION_TIME)
        else:
            self.expiration_time = datetime.now() + timedelta(minutes=PHONE_EXPIRATION_TIME)
        return super().save(*arg, **kwargs)
    
    def __str__(self):
        return f'{self.user.username} | {self.code}'
    
# =======================================================
class Post(BaseModel):
    title = models.CharField(max_length=255)
    desc = models.TextField()
    image = models.ImageField(upload_to='post_images/', validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg'])])
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='posts')

    def __str__(self):
        return f"{self.author.username} post: {self.title[:20]}"


class Comment(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')

    def __str__(self):
        return f"{self.author.username} comment on {self.post.id}"


class Like(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True, related_name='likes')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True, related_name='likes')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'post'], name='unique_post_like', condition=models.Q(post__isnull=False)),
            models.UniqueConstraint(fields=['user', 'comment'], name='unique_comment_like', condition=models.Q(comment__isnull=False)),
        ]


class Follow(BaseModel):
    follower = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='followers')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_followers')
        ]


class Story(BaseModel):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='stories')
    image = models.ImageField(upload_to='stories/', null=True, blank=True)
    video = models.FileField(upload_to='stories/', null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    expiration_time = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expiration_time:
            self.expiration_time = datetime.now() + timedelta(days=1) # 24 soatdan keyin o'chadi
        super().save(*args, **kwargs)