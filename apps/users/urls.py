from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('google/', views.GoogleLoginView.as_view(), name='auth-google'),
    path('linkedin/', views.LinkedInLoginView.as_view(), name='auth-linkedin'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('me/', views.MeView.as_view(), name='auth-me'),
    path('delete/', views.DeleteAccountView.as_view(), name='auth-delete'),
    path('refresh/', views.CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('password-reset/request/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', views.PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('password-reset/', views.PasswordResetView.as_view(), name='password-reset'),
    path('two-factor/verify/', views.TwoFactorVerifyView.as_view(), name='two-factor-verify'),
    path('two-factor/manage/', views.TwoFactorManageView.as_view(), name='two-factor-manage'),
    path('users/', views.UserManagementView.as_view(), name='user-management'),
    path('users/bulk-create/', views.BulkUserCreateView.as_view(), name='user-bulk-create'),
    path('users/<int:user_id>/', views.UserDetailView.as_view(), name='user-detail'),
    path('public-profile/', views.PublicProfileView.as_view(), name='public-profile'),
    path('public/<slug:slug>/', views.PublicProfileDetailView.as_view(), name='public-profile-detail'),
    path('goal/', views.JobSearchGoalView.as_view(), name='job-search-goal'),
]
