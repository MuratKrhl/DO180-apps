from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from axes.decorators import axes_dispatch
from axes.helpers import is_locked
from .models import LoginAttempt, UserSession, UserProfile
from .forms import CustomLoginForm
import logging

logger = logging.getLogger(__name__)

@never_cache
@csrf_protect
@axes_dispatch
def login_view(request):
    """Özel login view"""
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    
    # IP kontrolü
    if is_locked(request):
        messages.error(request, 'Çok fazla başarısız giriş denemesi. Lütfen daha sonra tekrar deneyin.')
        return render(request, 'authentication/login.html', {'form': CustomLoginForm(), 'locked': True})
    
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', False)
            
            # Kullanıcıyı doğrula
            user = authenticate(request, username=username, password=password)
            
            # Giriş denemesini kaydet
            LoginAttempt.objects.create(
                username=username,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                success=user is not None,
                failure_reason='' if user else 'Invalid credentials'
            )
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Remember me özelliği
                    if remember_me:
                        request.session.set_expiry(settings.SESSION_COOKIE_AGE * 24)  # 24x uzat
                    else:
                        request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                    
                    # Kullanıcı profilini oluştur/güncelle
                    profile, created = UserProfile.objects.get_or_create(user=user)
                    if created:
                        logger.info(f"Created profile for user: {user.username}")
                    
                    # Başarılı giriş mesajı
                    messages.success(request, f'Hoşgeldiniz, {user.get_full_name() or user.username}!')
                    
                    # Yönlendirme
                    next_url = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
                    return redirect(next_url)
                else:
                    messages.error(request, 'Hesabınız devre dışı bırakılmış.')
            else:
                messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
    else:
        form = CustomLoginForm()
    
    context = {
        'form': form,
        'locked': False,
    }
    return render(request, 'authentication/login.html', context)

@login_required
def logout_view(request):
    """Çıkış işlemi"""
    username = request.user.username
    
    # Kullanıcı oturumunu pasif yap
    UserSession.objects.filter(
        user=request.user,
        session_key=request.session.session_key
    ).update(is_active=False)
    
    logout(request)
    messages.info(request, f'{username}, başarıyla çıkış yaptınız.')
    return redirect(settings.LOGOUT_REDIRECT_URL)

@login_required
def profile_view(request):
    """Kullanıcı profil sayfası"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Aktif oturumlar
    active_sessions = UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-last_activity')
    
    # Son giriş denemeleri
    recent_attempts = LoginAttempt.objects.filter(
        username=request.user.username
    ).order_by('-timestamp')[:10]
    
    context = {
        'profile': profile,
        'active_sessions': active_sessions,
        'recent_attempts': recent_attempts,
    }
    return render(request, 'authentication/profile.html', context)

@login_required
def terminate_session(request, session_id):
    """Belirli bir oturumu sonlandır"""
    if request.method == 'POST':
        try:
            user_session = UserSession.objects.get(
                id=session_id,
                user=request.user
            )
            user_session.is_active = False
            user_session.save()
            
            # Django session'ını da sil
            from django.contrib.sessions.models import Session
            try:
                session = Session.objects.get(session_key=user_session.session_key)
                session.delete()
            except Session.DoesNotExist:
                pass
            
            return JsonResponse({'success': True})
        except UserSession.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Session not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def get_client_ip(request):
    """Gerçek IP adresini al"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# LDAP Test View (Development only)
def ldap_test_view(request):
    """LDAP bağlantısını test et (sadece development)"""
    if not settings.DEBUG:
        return JsonResponse({'error': 'Not available in production'})
    
    try:
        import ldap
        from django_auth_ldap.backend import LDAPBackend
        
        backend = LDAPBackend()
        ldap_user = backend.authenticate(request, username='test', password='test')
        
        return JsonResponse({
            'ldap_server': settings.AUTH_LDAP_SERVER_URI,
            'connection': 'OK' if ldap_user else 'Failed',
            'user_search_base': settings.AUTH_LDAP_USER_SEARCH.base_dn,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)})
