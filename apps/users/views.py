from rest_framework import generics, permissions, status
from rest_framework.response import Response
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
)
from .models import PasswordResetToken

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
            return Response({
                'user': data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
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
        
        # Generate tokens with custom lifetime based on remember_me
        from django.conf import settings
        from datetime import timedelta
        
        if remember_me:
            # Use longer token lifetime for "remember me"
            access_token_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('REMEMBER_TOKEN_LIFETIME', timedelta(days=30))
            # print(f"[LOGIN SUCCESS] Remember Me enabled - token lifetime: {access_token_lifetime}")
        else:
            access_token_lifetime = getattr(settings, 'SIMPLE_JWT', {}).get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=60))
            # print(f"[LOGIN SUCCESS] Standard login - token lifetime: {access_token_lifetime}")
        
        refresh = RefreshToken.for_user(user)
        
        # Set custom access token lifetime
        refresh.access_token.lifetime = access_token_lifetime
        
        user_data = UserSerializer(user).data
        # print(f"[LOGIN SUCCESS] User logged in: {user.email}")
        
        return Response({
            'user': user_data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
        return Response(status=204)


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
            
            return Response({
                'user': user_data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
            
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
