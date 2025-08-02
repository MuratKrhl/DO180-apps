from django.contrib.auth import logout
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.conf import settings
from .models import UserSession
import logging

logger = logging.getLogger(__name__)

class SessionTimeoutMiddleware:
    """Oturum zaman aşımı middleware'i"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            self.process_session_timeout(request)
            self.update_user_session(request)
        
        response = self.get_response(request)
        return response

    def process_session_timeout(self, request):
        """Oturum zaman aşımını kontrol et"""
        session_timeout = getattr(settings, 'SESSION_COOKIE_AGE', 1800)
        last_activity = request.session.get('last_activity')
        
        if last_activity:
            last_activity = timezone.datetime.fromisoformat(last_activity)
            if (timezone.now() - last_activity).seconds > session_timeout:
                logger.info(f"Session timeout for user: {request.user.username}")
                logout(request)
                return
        
        # Son aktivite zamanını güncelle
        request.session['last_activity'] = timezone.now().isoformat()

    def update_user_session(self, request):
        """Kullanıcı oturum bilgilerini güncelle"""
        try:
            user_session, created = UserSession.objects.get_or_create(
                user=request.user,
                session_key=request.session.session_key,
                defaults={
                    'ip_address': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                }
            )
            
            if not created:
                user_session.last_activity = timezone.now()
                user_session.ip_address = self.get_client_ip(request)
                user_session.save(update_fields=['last_activity', 'ip_address'])
                
        except Exception as e:
            logger.error(f"Error updating user session: {e}")

    def get_client_ip(self, request):
        """Gerçek IP adresini al"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
