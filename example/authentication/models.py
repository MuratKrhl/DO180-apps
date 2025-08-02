from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    """Kullanıcı profil bilgileri"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.CharField(max_length=100, blank=True, verbose_name="Departman")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    employee_id = models.CharField(max_length=50, blank=True, verbose_name="Personel ID")
    ldap_dn = models.CharField(max_length=500, blank=True, verbose_name="LDAP DN")
    last_ldap_sync = models.DateTimeField(null=True, blank=True, verbose_name="Son LDAP Senkronizasyonu")
    preferred_language = models.CharField(max_length=10, default='tr', verbose_name="Tercih Edilen Dil")
    timezone = models.CharField(max_length=50, default='Europe/Istanbul', verbose_name="Zaman Dilimi")
    
    class Meta:
        verbose_name = "Kullanıcı Profili"
        verbose_name_plural = "Kullanıcı Profilleri"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - Profil"

class LoginAttempt(models.Model):
    """Giriş denemeleri log'u"""
    username = models.CharField(max_length=150, verbose_name="Kullanıcı Adı")
    ip_address = models.GenericIPAddressField(verbose_name="IP Adresi")
    user_agent = models.TextField(verbose_name="User Agent")
    success = models.BooleanField(verbose_name="Başarılı")
    failure_reason = models.CharField(max_length=200, blank=True, verbose_name="Hata Nedeni")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Zaman")
    
    class Meta:
        verbose_name = "Giriş Denemesi"
        verbose_name_plural = "Giriş Denemeleri"
        ordering = ['-timestamp']

    def __str__(self):
        status = "Başarılı" if self.success else "Başarısız"
        return f"{self.username} - {status} ({self.timestamp})"

class UserSession(models.Model):
    """Aktif kullanıcı oturumları"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    session_key = models.CharField(max_length=40, unique=True, verbose_name="Oturum Anahtarı")
    ip_address = models.GenericIPAddressField(verbose_name="IP Adresi")
    user_agent = models.TextField(verbose_name="User Agent")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma")
    last_activity = models.DateTimeField(auto_now=True, verbose_name="Son Aktivite")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")
    
    class Meta:
        verbose_name = "Kullanıcı Oturumu"
        verbose_name_plural = "Kullanıcı Oturumları"
        ordering = ['-last_activity']

    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"

    @property
    def is_expired(self):
        """Oturumun süresi dolmuş mu?"""
        from django.conf import settings
        timeout = settings.SESSION_COOKIE_AGE
        return (timezone.now() - self.last_activity).seconds > timeout
