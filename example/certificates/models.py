from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from core.models import BaseModel
import json

class CertificateBase(BaseModel):
    """Sertifika temel modeli - Abstract"""
    
    STATUS_CHOICES = [
        ('valid', 'Geçerli'),
        ('expiring', 'Süresi Yaklaşıyor'),
        ('expired', 'Süresi Dolmuş'),
        ('revoked', 'İptal Edilmiş'),
        ('unknown', 'Bilinmiyor'),
    ]
    
    ENVIRONMENT_CHOICES = [
        ('production', 'Production'),
        ('test', 'Test'),
        ('development', 'Development'),
        ('staging', 'Staging'),
    ]
    
    # Temel Sertifika Bilgileri
    common_name = models.CharField(max_length=255, verbose_name="Common Name")
    subject = models.TextField(verbose_name="Subject", blank=True)
    issuer = models.TextField(verbose_name="Issuer", blank=True)
    serial_number = models.CharField(max_length=100, verbose_name="Serial Number", blank=True)
    
    # Tarih Bilgileri
    valid_from = models.DateTimeField(verbose_name="Geçerlilik Başlangıcı")
    valid_to = models.DateTimeField(verbose_name="Geçerlilik Sonu")
    
    # Durum ve Çevre
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='valid', verbose_name="Durum")
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, verbose_name="Ortam")
    
    # İlişkili Sistemler
    server_name = models.CharField(max_length=255, verbose_name="Sunucu Adı", blank=True)
    application_name = models.CharField(max_length=255, verbose_name="Uygulama Adı", blank=True)
    
    # Teknik Detaylar
    key_size = models.IntegerField(verbose_name="Anahtar Boyutu", null=True, blank=True)
    signature_algorithm = models.CharField(max_length=100, verbose_name="İmza Algoritması", blank=True)
    public_key_algorithm = models.CharField(max_length=100, verbose_name="Public Key Algoritması", blank=True)
    
    # Senkronizasyon
    last_sync = models.DateTimeField(verbose_name="Son Senkronizasyon", auto_now=True)
    sync_source = models.CharField(max_length=50, verbose_name="Senkronizasyon Kaynağı", blank=True)
    
    class Meta:
        abstract = True
        ordering = ['valid_to', 'common_name']
    
    def __str__(self):
        return f"{self.common_name} ({self.get_status_display()})"
    
    @property
    def days_until_expiry(self):
        """Sona kaç gün kaldığını hesapla"""
        if self.valid_to:
            delta = self.valid_to.date() - timezone.now().date()
            return delta.days
        return None
    
    @property
    def is_expiring_soon(self):
        """30 gün içinde süresi dolacak mı?"""
        days = self.days_until_expiry
        return days is not None and 0 <= days <= 30
    
    @property
    def is_expired(self):
        """Süresi dolmuş mu?"""
        return self.valid_to < timezone.now()
    
    @property
    def status_color(self):
        """Durum rengini döndür"""
        if self.is_expired:
            return 'danger'
        elif self.is_expiring_soon:
            return 'warning'
        else:
            return 'success'
    
    def update_status(self):
        """Durumu otomatik güncelle"""
        if self.is_expired:
            self.status = 'expired'
        elif self.is_expiring_soon:
            self.status = 'expiring'
        else:
            self.status = 'valid'
        self.save(update_fields=['status'])

class KdbCertificate(CertificateBase):
    """KDB (Key Database) Sertifikaları"""
    
    SOURCE_CHOICES = [
        ('appviewx', 'AppViewX API'),
        ('sql_db', 'SQL Database'),
        ('ansible', 'Ansible Output'),
        ('manual', 'Manuel Giriş'),
    ]
    
    # KDB Özel Alanları
    kdb_file_path = models.CharField(max_length=500, verbose_name="KDB Dosya Yolu", blank=True)
    password_file_path = models.CharField(max_length=500, verbose_name="Password Dosya Yolu", blank=True)
    certificate_label = models.CharField(max_length=255, verbose_name="Sertifika Etiketi", blank=True)
    
    # AppViewX Entegrasyonu
    appviewx_id = models.CharField(max_length=100, verbose_name="AppViewX ID", blank=True, unique=True, null=True)
    appviewx_data = models.JSONField(verbose_name="AppViewX Raw Data", default=dict, blank=True)
    
    # Kaynak Bilgisi
    data_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual', verbose_name="Veri Kaynağı")
    
    class Meta:
        verbose_name = "KDB Sertifikası"
        verbose_name_plural = "KDB Sertifikaları"
        unique_together = ['common_name', 'serial_number', 'server_name']

class JavaCertificate(CertificateBase):
    """Java Keystore Sertifikaları"""
    
    KEYSTORE_TYPE_CHOICES = [
        ('jks', 'JKS (Java KeyStore)'),
        ('pkcs12', 'PKCS12'),
        ('jceks', 'JCEKS'),
        ('pkcs11', 'PKCS11'),
    ]
    
    # Java Özel Alanları
    keystore_path = models.CharField(max_length=500, verbose_name="Keystore Dosya Yolu")
    keystore_type = models.CharField(max_length=20, choices=KEYSTORE_TYPE_CHOICES, default='jks', verbose_name="Keystore Tipi")
    alias_name = models.CharField(max_length=255, verbose_name="Alias Adı")
    
    # Keytool Çıktısı
    keytool_output = models.TextField(verbose_name="Keytool Raw Output", blank=True)
    
    # SSH Bağlantı Bilgileri
    ssh_host = models.CharField(max_length=255, verbose_name="SSH Host", blank=True)
    ssh_user = models.CharField(max_length=100, verbose_name="SSH Kullanıcı", blank=True)
    
    class Meta:
        verbose_name = "Java Sertifikası"
        verbose_name_plural = "Java Sertifikaları"
        unique_together = ['keystore_path', 'alias_name', 'ssh_host']

class CertificateAlert(BaseModel):
    """Sertifika Uyarıları"""
    
    ALERT_TYPE_CHOICES = [
        ('expiring_90', '90 Gün Kala'),
        ('expiring_60', '60 Gün Kala'),
        ('expiring_30', '30 Gün Kala'),
        ('expiring_15', '15 Gün Kala'),
        ('expiring_7', '7 Gün Kala'),
        ('expiring_1', '1 Gün Kala'),
        ('expired', 'Süresi Dolmuş'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('sent', 'Gönderildi'),
        ('failed', 'Başarısız'),
    ]
    
    # Sertifika Referansları (Generic Foreign Key kullanabiliriz)
    certificate_type = models.CharField(max_length=20, choices=[('kdb', 'KDB'), ('java', 'Java')])
    certificate_id = models.PositiveIntegerField()
    certificate_common_name = models.CharField(max_length=255, verbose_name="Sertifika CN")
    
    # Uyarı Detayları
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES, verbose_name="Uyarı Tipi")
    alert_date = models.DateTimeField(verbose_name="Uyarı Tarihi", auto_now_add=True)
    expiry_date = models.DateTimeField(verbose_name="Sona Erme Tarihi")
    
    # Bildirim Durumu
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Durum")
    sent_to = models.TextField(verbose_name="Gönderilen E-postalar", blank=True)
    sent_at = models.DateTimeField(verbose_name="Gönderilme Zamanı", null=True, blank=True)
    error_message = models.TextField(verbose_name="Hata Mesajı", blank=True)
    
    class Meta:
        verbose_name = "Sertifika Uyarısı"
        verbose_name_plural = "Sertifika Uyarıları"
        unique_together = ['certificate_type', 'certificate_id', 'alert_type']
        ordering = ['-alert_date']

class CertificateNotificationSettings(BaseModel):
    """Sertifika Bildirim Ayarları"""
    
    name = models.CharField(max_length=100, verbose_name="Ayar Adı")
    
    # E-posta Ayarları
    recipient_emails = models.TextField(verbose_name="Alıcı E-postalar", help_text="Her satıra bir e-posta")
    cc_emails = models.TextField(verbose_name="CC E-postalar", blank=True, help_text="Her satıra bir e-posta")
    
    # Filtre Ayarları
    environments = models.JSONField(verbose_name="Ortamlar", default=list, blank=True)
    certificate_types = models.JSONField(verbose_name="Sertifika Tipleri", default=list, blank=True)
    applications = models.JSONField(verbose_name="Uygulamalar", default=list, blank=True)
    
    # Bildirim Zamanlaması
    alert_days = models.JSONField(verbose_name="Uyarı Günleri", default=list, help_text="[90, 60, 30, 15, 7, 1]")
    send_weekly_report = models.BooleanField(default=True, verbose_name="Haftalık Rapor Gönder")
    weekly_report_day = models.IntegerField(default=1, verbose_name="Haftalık Rapor Günü (0=Pazartesi)")
    
    class Meta:
        verbose_name = "Bildirim Ayarı"
        verbose_name_plural = "Bildirim Ayarları"

class CertificateSyncLog(BaseModel):
    """Sertifika Senkronizasyon Logları"""
    
    STATUS_CHOICES = [
        ('running', 'Çalışıyor'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('partial', 'Kısmi Başarılı'),
    ]
    
    SOURCE_CHOICES = [
        ('appviewx', 'AppViewX API'),
        ('sql_db', 'SQL Database'),
        ('ansible', 'Ansible'),
        ('ssh_keytool', 'SSH + Keytool'),
        ('manual', 'Manuel'),
    ]
    
    # Senkronizasyon Bilgileri
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, verbose_name="Kaynak")
    certificate_type = models.CharField(max_length=20, choices=[('kdb', 'KDB'), ('java', 'Java')], verbose_name="Sertifika Tipi")
    
    # Durum ve Zaman
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running', verbose_name="Durum")
    started_at = models.DateTimeField(verbose_name="Başlangıç", auto_now_add=True)
    completed_at = models.DateTimeField(verbose_name="Bitiş", null=True, blank=True)
    
    # İstatistikler
    total_processed = models.IntegerField(default=0, verbose_name="Toplam İşlenen")
    successful_count = models.IntegerField(default=0, verbose_name="Başarılı")
    failed_count = models.IntegerField(default=0, verbose_name="Başarısız")
    new_count = models.IntegerField(default=0, verbose_name="Yeni Eklenen")
    updated_count = models.IntegerField(default=0, verbose_name="Güncellenen")
    
    # Detaylar
    log_details = models.JSONField(verbose_name="Log Detayları", default=dict, blank=True)
    error_details = models.TextField(verbose_name="Hata Detayları", blank=True)
    
    class Meta:
        verbose_name = "Senkronizasyon Logu"
        verbose_name_plural = "Senkronizasyon Logları"
        ordering = ['-started_at']
    
    @property
    def duration(self):
        """Süreyi hesapla"""
        if self.completed_at:
            return self.completed_at - self.started_at
        return timezone.now() - self.started_at
    
    @property
    def success_rate(self):
        """Başarı oranını hesapla"""
        if self.total_processed > 0:
            return round((self.successful_count / self.total_processed) * 100, 2)
        return 0
