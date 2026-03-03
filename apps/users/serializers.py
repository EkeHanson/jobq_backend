from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PasswordResetToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        extra_kwargs = {
            'username': {'required': False},
            'email': {'required': False},
        }


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirmPassword = serializers.CharField(write_only=True, required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'confirmPassword', 'first_name', 'last_name']

    def validate(self, data):
        # If confirmPassword is provided, validate it matches
        if data.get('confirmPassword') and data['password'] != data['confirmPassword']:
            raise serializers.ValidationError({'confirmPassword': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        # Remove confirmPassword from validated data
        validated_data.pop('confirmPassword', None)
        
        # Generate username from email if not provided
        username = validated_data.get('username')
        if not username:
            username = validated_data.get('email', 'user').split('@')[0]
        
        # Make username unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # print(f"[SERIALIZER] Creating user with username={username}, email={validated_data.get('email')}")
        
        try:
            user = User.objects.create_user(
                username=username,
                email=validated_data.get('email'),
                password=validated_data['password'],
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
            )
            # print(f"[SERIALIZER] User created successfully: ID={user.id}, email={user.email}, username={user.username}")
            return user
        except Exception as e:
            print(f"[SERIALIZER] Error creating user: {str(e)}")
            raise


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting password reset"""
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError('User with this email does not exist.')
        return value


class PasswordResetVerifySerializer(serializers.Serializer):
    """Serializer for verifying reset token"""
    email = serializers.EmailField()
    token = serializers.CharField()

    def validate(self, data):
        email = data.get('email')
        token = data.get('token')
        
        try:
            user = User.objects.get(email=email)
            reset_token = PasswordResetToken.objects.get(user=user, token=token)
            
            if not reset_token.is_valid():
                raise serializers.ValidationError('Invalid or expired reset token.')
        except (User.DoesNotExist, PasswordResetToken.DoesNotExist):
            raise serializers.ValidationError('Invalid email or token.')
        
        return data


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for resetting password with token"""
    email = serializers.EmailField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        email = data.get('email')
        token = data.get('token')
        
        try:
            user = User.objects.get(email=email)
            reset_token = PasswordResetToken.objects.get(user=user, token=token)
            
            if not reset_token.is_valid():
                raise serializers.ValidationError('Invalid or expired reset token.')
            
            # Store token object for later use
            self.reset_token = reset_token
            self.user = user
        except (User.DoesNotExist, PasswordResetToken.DoesNotExist):
            raise serializers.ValidationError('Invalid email or token.')
        
        return data
