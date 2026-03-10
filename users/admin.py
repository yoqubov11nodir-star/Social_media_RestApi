from django.contrib import admin
from .models import CodeVerifiy, CustomUser

admin.site.register(CustomUser)
admin.site.register(CodeVerifiy)