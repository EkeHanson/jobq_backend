from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """JWT authentication that supports token in Authorization header or in a cookie.

    This allows the frontend to store the access token in a cookie (or receive it via
    the backend) and still authenticate requests.
    """

    def authenticate(self, request):
        # Try standard Authorization header first
        header = self.get_header(request)
        raw_token = self.get_raw_token(header) if header is not None else None

        # Fall back to cookie if header is not present
        if raw_token is None:
            raw_token = request.COOKIES.get('access_token')

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        
        # Check if user account is suspended
        if user.is_suspended:
            return None
        
        return user, validated_token
