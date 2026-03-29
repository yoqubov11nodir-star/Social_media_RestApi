from django.urls import path

from .views import (
    SignUpView, CodeVerify, GetNewCode, UserChangeInfoView, 
    UserPhotoStatusView, LoginView, LogoutView, LoginRefresh,
    ForgotPasswordView, ResetPasswordView,PostListCreateAPIView, 
    CommentListCreateAPIView, LikeToggleAPIView, FollowAPIView, 
    StoryListCreateAPIView, ProfileView
)

urlpatterns = [
    path('sign-up/', SignUpView.as_view()),
    path('code-verify/', CodeVerify.as_view()),
    path('get-new-code/', GetNewCode.as_view()),
    path('change-info/', UserChangeInfoView.as_view()),
    path('change-photo/', UserPhotoStatusView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('loginrefresh/', LoginRefresh.as_view()),
    path('forgot-password/', ForgotPasswordView.as_view()),
    path('reset-password/', ResetPasswordView.as_view()),

    path('posts/', PostListCreateAPIView.as_view(), name='post-list'),
    path('comments/', CommentListCreateAPIView.as_view(), name='comment-list'),
    path('likes/toggle/', LikeToggleAPIView.as_view(), name='like-toggle'),
    path('follow/', FollowAPIView.as_view(), name='follow'),
    path('stories/', StoryListCreateAPIView.as_view(), name='story-list'),
    path('me/', ProfileView.as_view(), name='profile-me'),

]