from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('google/', views.GoogleLoginView.as_view(), name='auth-google'),
    path('linkedin/', views.LinkedInLoginView.as_view(), name='auth-linkedin'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('me/', views.MeView.as_view(), name='auth-me'),
    path('delete/', views.DeleteAccountView.as_view(), name='auth-delete'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password-reset/request/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', views.PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('password-reset/', views.PasswordResetView.as_view(), name='password-reset'),
]
