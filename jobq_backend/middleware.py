import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Log all incoming requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # print(f"\n[MIDDLEWARE] ========== INCOMING REQUEST ==========")
        # print(f"[MIDDLEWARE] Method: {request.method}")
        # print(f"[MIDDLEWARE] Path: {request.path}")
        # print(f"[MIDDLEWARE] Full path: {request.path_info}")
        # print(f"[MIDDLEWARE] Content-Type: {request.META.get('CONTENT_TYPE', 'None')}")
        # print(f"[MIDDLEWARE] Host: {request.META.get('HTTP_HOST', 'None')}")
        # print(f"[MIDDLEWARE] Origin: {request.META.get('HTTP_ORIGIN', 'None')}")
        # print(f"[MIDDLEWARE] ========================================\n")
        
        response = self.get_response(request)
        
        # print(f"[MIDDLEWARE] Response Status: {response.status_code}")
        
        return response
