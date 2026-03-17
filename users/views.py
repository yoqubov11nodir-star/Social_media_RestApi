from django.shortcuts import render
from rest_framework.generics import CreateAPIView
from rest_framework import permissions, status
from .serializers import SignupSerialzier, UserChangeInfoSerializer, PhotoStatusSerializer, LoginSerializer, ResetPasswordSerializer, ForgotPasswordSerializer, PostSerializer, ProfileSerializer, CommentSerializer, LikeSerializer, FollowSerializer, StorySerializer
from .models import CustomUser, NEW, CODE_VERIFIY, DONE, PHOTO_DONE, VIA_EMAIL, VIA_PHONE, Post, Comment, Like, Follow, Story
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, UpdateAPIView
from datetime import datetime
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.core.mail import send_mail
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt import token_blacklist

class SignUpView(CreateAPIView):
    permission_classes = (permissions.AllowAny, )
    serializer_class = SignupSerialzier
    queryset = CustomUser.objects.all()

class CodeVerify(APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def post(self, request):
        user = request.user
        code = request.data.get('code')
        codes = user.verify_codes.filter(code=code, expiration_time__gte=datetime.now(), is_active=False)

        if not codes.exists():
            raise ValidationError({"message": "Kodingiz xato yoki eskirgan", "status": status.HTTP_400_BAD_REQUEST})
        
        codes.update(is_active=True)

        if user.auth_status == NEW:
            user.auth_status = CODE_VERIFIY
            user.save()

        response_data = {
            "message": "Kod Tasdiqlandi",
            "status": status.HTTP_200_OK,
            "access": user.token()['access'],
            "refresh": user.token()['refresh']
        }
        return Response(response_data)

class GetNewCode(APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def get(self, request):
        user = request.user     
        code = user.verify_codes.filter(expiration_time__gte=datetime.now(), is_active=False)
        
        if code.exists():
            raise ValidationError({"message": "Sizda hali active kod bor", "status": status.HTTP_400_BAD_REQUEST})
        
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
        
        return Response({
            "message": "Kod yuborildi",
            "status": status.HTTP_201_CREATED,
        })
    
class UserChangeInfoView(APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def put(self, request):
        user = request.user
        serializer = UserChangeInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(instance=user, validated_data=serializer.validated_data)

        return Response({
            "message": "Ma'lumot qo'shildi",
            "status": status.HTTP_200_OK,
            "access": user.token()['access'],
            "refresh": user.token()['refresh']
        })
    
class UserPhotoStatusView(APIView):
    permission_classes = (permissions.IsAuthenticated, ) 

    def patch(self, request):
        user = request.user
        serializer = PhotoStatusSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.update(instance=user, validated_data=serializer.validated_data)

        return Response({
            "message": "Rasm qo'shildi",
            "status": status.HTTP_201_CREATED,
            "access": user.token()['access'],
            "refresh": user.token()['refresh']
        })
    
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def post(self, request):
        refresh = request.data.get('refresh', None)

        try:
            refresh_token = RefreshToken(refresh)
            refresh_token.blacklist()
            return Response({
                'status': status.HTTP_200_OK,
                'message': "Tizimdan chiqdingiz"
            })
        except Exception as e:
            raise ValidationError(detail=f'Xatolik: {e}')
        
class LoginRefresh(APIView):
    permission_classes = (permissions.AllowAny, )

    def post(self, request):
        refresh = request.data.get('refresh', None)

        try:
            refresh_token = RefreshToken(refresh)
            return Response({
                'status': status.HTTP_201_CREATED,
                'access': str(refresh_token.access_token)
            })
        except Exception as e:
            raise ValidationError(detail=f'Xatolik: {e}')
        
class ForgotPasswordView(APIView):
    permission_classes = (permissions.AllowAny, )

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({
            "status": True,
            "message": "Tasdiqlash kodi yuborildi.",
        }, status=status.HTTP_200_OK)

class ResetPasswordView(UpdateAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = (permissions.IsAuthenticated, )

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        if user.auth_status != CODE_VERIFIY:
            raise ValidationError("Avval kodni tasdiqlashingiz kerak.")

        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        user.auth_status = DONE
        user.save()

        return Response({
            'status': True,
            'message': "Parolingiz muvaffaqiyatli o'zgartirildi.",
            'access': user.token()['access'],
            'refresh': user.token()['refresh']
        }, status=status.HTTP_200_OK)

class PostListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        posts = Post.objects.all().order_by('-created_at')
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CommentListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        comments = Comment.objects.filter(parent__isnull=True) # main commentlar
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LikeToggleAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LikeSerializer(data=request.data)
        if serializer.is_valid():
            post = serializer.validated_data.get('post')
            comment = serializer.validated_data.get('comment')
            
            like_qs = Like.objects.filter(user=request.user, post=post, comment=comment)
            if like_qs.exists():
                like_qs.delete()
                return Response({"message": "Like olib tashlandi"}, status=status.HTTP_204_NO_CONTENT)
            
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FollowAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FollowSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['following'] == request.user:
                return Response({"error": "O'zingizga ergasha olmaysiz"}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(follower=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StoryListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from datetime import datetime
        stories = Story.objects.filter(expiration_time__gt=datetime.now())
        serializer = StorySerializer(stories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = StorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)