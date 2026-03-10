from rest_framework.generics import CreateAPIView
from rest_framework import permissions
from .serializers import SignupSerialzier
from .models import CustomUser

class SignUpView(CreateAPIView):
    permission_classes = (permissions.AllowAny, )
    serializer_class = SignupSerialzier
    queryset = CustomUser.objects.all()