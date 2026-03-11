from datetime import timedelta

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from .serializers import (
    UserSerializer, 
    RegisterSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    PasswordResetSerializer,
    TwoFactorVerifySerializer,
    TwoFactorEnableSerializer,
)
from .models import PasswordResetToken, TwoFactorToken

User = get_user_model()



class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        # print(f"[REGISTER ATTEMPT] Email: {request.data.get('email')}")
        # print(f"[REGISTER ATTEMPT] Username: {request.data.get('username')}")
        # print(f"[REGISTER DEBUG] Full request data: {request.data}")
        
        # override to return tokens on registration
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            # print(f"[REGISTER FAILED] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = serializer.save()
            # print(f"[REGISTER SUCCESS] User created: {user.email}, username: {user.username}")
            # print(f"[REGISTER DEBUG] User ID: {user.id}, is_active: {user.is_active}")
            
            refresh = RefreshToken.for_user(user)
            data = serializer.data
            return Response(
                {
                    'user': data,
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            print(f"[REGISTER EXCEPTION] Error creating user: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(generics.GenericAPIView):
    serializer_class = RegisterSerializer  # not used except for docs
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # print(f"\n[LOGIN VIEW] ========== LOGIN REQUEST RECEIVED ==========")
        # print(f"[LOGIN VIEW] Request method: {request.method}")
        # print(f"[LOGIN VIEW] Request path: {request.path}")
        # print(f"[LOGIN VIEW] Request data keys: {list(request.data.keys()) if hasattr(request, 'data') else 'N/A'}")
        # print(f"[LOGIN VIEW] Full request.data: {request.data if hasattr(request, 'data') else 'N/A'}")
        # print(f"[LOGIN VIEW] =======================================\n")
        
        identifier = request.data.get('username') or request.data.get('email')
        password = request.data.get('password')
        remember_me = request.data.get('remember_me', False)
        
        # print(f"[LOGIN ATTEMPT] Email/Username: {identifier}")
        # print(f"[LOGIN ATTEMPT] Remember Me: {remember_me}")
        # print(f"[LOGIN DEBUG] All users in database: {list(User.objects.all().values('id', 'username', 'email'))}")
        
        user = None
        if identifier:
            user = User.objects.filter(username=identifier).first()
            if not user:
                user = User.objects.filter(email=identifier).first()
        
        if not user:
            # print(f"[LOGIN FAILED] User not found with identifier: {identifier}")
            # print(f"[LOGIN DEBUG] Searched for username: '{identifier}', email: '{identifier}'")
            return Response({'detail': 'Invalid credentials - user not found'}, status=400)
        
        if not user.check_password(password):
            # print(f"[LOGIN FAILED] Password check failed for user: {identifier}")
            return Response({'detail': 'Invalid credentials - incorrect password'}, status=400)
        
        # Check if user account is suspended
        if user.is_suspended:
            return Response(
                {'detail': 'Your account has been suspended. Please contact support for assistance.'},
                status=403
            )
        
        # Check if user account is active
        if not user.is_active:
            return Response(
                {'detail': 'Your account has been deactivated. Please contact support for assistance.'},
                status=403
            )
        
        # Check if 2FA is enabled
        if user.is_2fa_enabled:
            # Delete old unused tokens for this user
            TwoFactorToken.objects.filter(user=user, is_used=False).delete()
            
            # Create new 2FA token
            two_factor_token = TwoFactorToken.objects.create(user=user)
            
            # Send 2FA code via email
            try:
                send_mail(
                    subject='Your Login Verification Code',
                    message=f'Your verification code is: {two_factor_token.token}\n\nThis code expires in 10 minutes.\n\nIf you did not request this, please ignore this email.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                return Response(
                    {'detail': 'Failed to send verification code. Please try again.'},
                    status=500
                )
            
            # Return response indicating 2FA is required
            return Response(
                {
                    'require_2fa': True,
                    'email': user.email,
                    'message': 'A verification code has been sent to your email.'
                },
                status=200
            )
        
        # Generate tokens with custom lifetime based on remember_me
        from django.conf import settings
        from datetime import timedelta
        
        if remember_me:
            # Use longer token lifetime for "remember me" - 30 days
            access_token_lifetime = timedelta(days=30)
            refresh_token_lifetime = timedelta(days=30)
        else:
            access_token_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=60))
            refresh_token_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('REFRESH_TOKEN_LIFETIME', timedelta(days=1))
        
        refresh = RefreshToken.for_user(user)
        
        # Set custom token lifetimes
        refresh.access_token.lifetime = access_token_lifetime
        refresh.lifetime = refresh_token_lifetime
        
        user_data = UserSerializer(user).data

        return Response(
            {
                'user': user_data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # If a refresh token is sent in the body, blacklist it.
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass

        return Response(status=204)


class CookieTokenRefreshView(generics.GenericAPIView):
    """Refresh access token using the supplied refresh token."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'Refresh token missing.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data={'refresh': refresh_token})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class GoogleLoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Handle Google OAuth login.
        Expects: { "token": "google_id_token" }
        """
        token = request.data.get('token')
        
        if not token:
            return Response(
                {'detail': 'Google token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify the Google token and get user info
            user_info = self.verify_google_token(token)
            
            if not user_info:
                return Response(
                    {'detail': 'Invalid Google token'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            email = user_info.get('email')
            google_id = user_info.get('sub')
            
            if not email:
                return Response(
                    {'detail': 'Email not provided by Google'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find or create user
            user = User.objects.filter(email=email).first()
            
            if not user:
                # Create new user
                username = email.split('@')[0]
                # Ensure unique username
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=None  # No password for OAuth users
                )
                user.is_active = True
                user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data
            
            return Response(
                {
                    'user': user_data,
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            )
            
        except Exception as e:
            return Response(
                {'detail': f'Google authentication failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def verify_google_token(self, token):
        """
        Verify Google ID token and return user info.
        In production, verify with Google's public keys.
        For development, we decode and validate the token structure.
        """
        import jwt
        import requests
        from django.conf import settings
        
        try:
            # In production, fetch Google's public keys and verify
            # For now, we'll decode and do basic validation
            # This is a simplified version - in production use google-auth library
            
            # Get Google client ID from settings or environment
            google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', 
                '773400491834-4nm9tdgvh2ghehj1di55gpcmten1coqg.apps.googleusercontent.com')
            
            # Decode without verification for development
            # In production, use google.oauth2.id_token.verify_oauth2_token
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Verify issuer
            if decoded.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
                return None
            
            # Verify audience matches our client ID
            aud = decoded.get('aud')
            if aud != google_client_id:
                return None
            
            # Check if token is expired
            import time
            if decoded.get('exp', 0) < time.time():
                return None
            
            return decoded
            
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None


class LinkedInLoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        return Response({'detail': 'Not implemented'}, status=501)


class DeleteAccountView(generics.GenericAPIView):
    """Delete user account and all associated data"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Delete account requires:
        1. User password confirmation
        2. This will permanently delete:
           - User profile
           - All job applications
           - All saved jobs
           - All notifications
           - All subscriptions
        """
        password = request.data.get('password')
        
        if not password:
            return Response(
                {'detail': 'Password is required to delete account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # Verify password
        if not user.check_password(password):
            return Response(
                {'detail': 'Invalid password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user email before deletion for logging
        user_email = user.email
        
        # Delete all related data
        # Delete profile and related data
        try:
            from apps.profiles.models import Profile
            profile = Profile.objects.filter(user=user).first()
            if profile:
                # Delete related objects
                profile.skills.all().delete()
                profile.experiences.all().delete()
                profile.education.all().delete()
                profile.certifications.all().delete()
                profile.resumes.all().delete()
                profile.delete()
        except Exception:
            pass
        
        # Delete applications
        try:
            from apps.applications.models import Application
            Application.objects.filter(user=user).delete()
        except Exception:
            pass
        
        # Delete jobs (if user is employer)
        try:
            from apps.jobs.models import Job
            Job.objects.filter(employer=user).delete()
        except Exception:
            pass
        
        # Delete notifications
        try:
            from apps.notifications.models import Notification
            Notification.objects.filter(user=user).delete()
        except Exception:
            pass
        
        # Delete subscriptions
        try:
            from apps.subscriptions.models import Subscription
            Subscription.objects.filter(user=user).delete()
        except Exception:
            pass
        
        # Delete the user account
        user.delete()
        
        return Response(
            {
                'detail': 'Account deleted successfully',
                'deleted_email': user_email
            },
            status=status.HTTP_200_OK
        )


class PasswordResetRequestView(generics.GenericAPIView):
    """Request a password reset token via email"""
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        
        # Delete old tokens for this user
        PasswordResetToken.objects.filter(user=user, is_used=False).delete()
        
        # Create new reset token
        reset_token = PasswordResetToken.objects.create(user=user)
        
        # Build reset link
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token.token}&email={user.email}"
        
        # Send email
        try:
            send_mail(
                subject='Password Reset Request',
                message=f'Click the link below to reset your password:\n\n{reset_url}\n\nThis link expires in 1 hour.\n\nIf you did not request this, please ignore this email.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {'detail': f'Failed to send reset email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(
            {'detail': 'Password reset link sent to your email'},
            status=status.HTTP_200_OK
        )


class PasswordResetVerifyView(generics.GenericAPIView):
    """Verify that a reset token is valid"""
    serializer_class = PasswordResetVerifySerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return Response(
            {'detail': 'Token is valid'},
            status=status.HTTP_200_OK
        )


class PasswordResetView(generics.GenericAPIView):
    """Reset password using a valid token"""
    serializer_class = PasswordResetSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get the user and token from serializer
        user = serializer.user
        reset_token = serializer.reset_token
        new_password = serializer.validated_data['new_password']
        
        # Update password
        user.set_password(new_password)
        user.save()
        
        # Mark token as used
        reset_token.is_used = True
        reset_token.save()
        
        # Delete all other unused tokens for this user
        PasswordResetToken.objects.filter(user=user, is_used=False).delete()
        
        return Response(
            {'detail': 'Password reset successfully'},
            status=status.HTTP_200_OK
        )


class TwoFactorVerifyView(generics.GenericAPIView):
    """Verify 2FA code and return tokens"""
    serializer_class = TwoFactorVerifySerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.user
        two_factor_token = serializer.two_factor_token
        remember_me = request.data.get('remember_me', False)
        
        # Mark token as verified
        two_factor_token.is_verified = True
        two_factor_token.save()
        
        # Generate tokens with custom lifetime based on remember_me
        from datetime import timedelta
        
        if remember_me:
            access_token_lifetime = timedelta(days=30)
            refresh_token_lifetime = timedelta(days=30)
        else:
            access_token_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=60))
            refresh_token_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('REFRESH_TOKEN_LIFETIME', timedelta(days=1))
        
        refresh = RefreshToken.for_user(user)
        
        # Set custom token lifetimes
        refresh.access_token.lifetime = access_token_lifetime
        refresh.lifetime = refresh_token_lifetime
        
        user_data = UserSerializer(user).data
        
        return Response(
            {
                'user': user_data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        )


class TwoFactorManageView(generics.GenericAPIView):
    """Enable or disable 2FA for the current user"""
    serializer_class = TwoFactorEnableSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        enable = serializer.validated_data['enable']
        
        user.is_2fa_enabled = enable
        user.save()
        
        if enable:
            return Response(
                {'detail': 'Two-factor authentication has been enabled.'},
                status=status.HTTP_200_OK
            )
        else:
            # Delete all unused 2FA tokens when disabling
            TwoFactorToken.objects.filter(user=user, is_used=False).delete()
            return Response(
                {'detail': 'Two-factor authentication has been disabled.'},
                status=status.HTTP_200_OK
            )


class UserManagementView(generics.GenericAPIView):
    """Admin endpoint to manage user accounts (suspend/unsuspend)"""
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, *args, **kwargs):
        """List all users (paginated)"""
        from django.core.paginator import Paginator
        
        users = User.objects.all().order_by('-date_joined')
        paginator = Paginator(users, 20)
        page = request.query_params.get('page', 1)
        
        try:
            users_page = paginator.page(page)
        except:
            users_page = paginator.page(1)
        
        serializer = UserSerializer(users_page.object_list, many=True)
        return Response({
            'results': serializer.data,
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page
        })
    
    def post(self, request, *args, **kwargs):
        """Suspend or unsuspend a user"""
        user_id = request.data.get('user_id')
        action = request.data.get('action')  # 'suspend' or 'unsuspend'
        reason = request.data.get('reason', '')
        
        if not user_id:
            return Response(
                {'detail': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if action not in ['suspend', 'unsuspend']:
            return Response(
                {'detail': 'action must be either "suspend" or "unsuspend"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if action == 'suspend':
            user.is_suspended = True
            user.suspension_reason = reason or 'Suspended by admin'
            user.suspended_at = timezone.now()
            user.save()
            return Response({
                'detail': f'User {user.email} has been suspended',
                'user': UserSerializer(user).data
            })
        else:
            user.is_suspended = False
            user.suspension_reason = ''
            user.suspended_at = None
            user.save()
            return Response({
                'detail': f'User {user.email} has been unsuspended',
                'user': UserSerializer(user).data
            })
