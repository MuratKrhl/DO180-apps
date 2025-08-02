from django.db import models
from core.models import BaseModel
from django.core.validators import MinValueValidator, MaxValueValidator
import socket
from datetime import datetime

class Server(BaseModel):
    """Sunucu modeli"""
    ENVIRONMENT_CHOICES = [
        ('prod', 'Production'),
        ('test', 'Test'),
        ('dev', 'Development'),
        ('stage', 'Staging'),
    ]
    
    OS_CHOICES = [
        ('linux', 'Linux'),
        ('aix', 'AIX'),
        ('windows', 'Windows'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('inactive', 'Pasif'),
        ('maintenance', 'Bakımda'),
        ('decommissioned', 'Hizmet Dışı'),
    ]
    
    hostname = models.CharField(max_length=100, unique=True, verbose_name="Hostname")
    ip_address = models.GenericIPAddressField(verbose_name="IP Adresi")
    operating_system = models.CharField(max_length=20, choices=OS_CHOICES, verbose_name="İşletim Sistemi")
    environment = models.CharField(max_length=10, choices=ENVIRONMENT_CHOICES, verbose_name="Ortam")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Durum")
    cpu_cores = models.PositiveIntegerField(verbose_name="CPU Çekirdek Sayısı")
    memory_gb = models.PositiveIntegerField(verbose_name="Bellek (GB)")
    disk_gb = models.PositiveIntegerField(verbose_name="Disk (GB)")
    location = models.CharField(max_length=100, verbose_name="Lokasyon")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    
    # Monitoring alanları
    last_ping = models.DateTimeField(null=True, blank=True, verbose_name="Son Ping")
    ping_status = models.BooleanField(default=False, verbose_name="Ping Durumu")
    
    # Sertifika bilgileri
    ssl_certificates = models.JSONField(default=list, blank=True, verbose_name="SSL Sertifikaları")
    
    class Meta:
        verbose_name = "Sunucu"
        verbose_name_plural = "Sunucular"
        ordering = ['hostname']

    def __str__(self):
        return f"{self.hostname} ({self.environment})"
    
    @property
    def status_color(self):
        """Durum rengi"""
        colors = {
            'active': 'success',
            'inactive': 'secondary',
            'maintenance': 'warning',
            'decommissioned': 'danger'
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def environment_color(self):
        """Ortam rengi"""
        colors = {
            'prod': 'danger',
            'test': 'warning',
            'dev': 'info',
            'stage': 'primary'
        }
        return colors.get(self.environment, 'secondary')
    
    def check_connectivity(self):
        """Sunucu bağlantısını kontrol et"""
        try:
            socket.setdefaulttimeout(5)
            result = socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex((str(self.ip_address), 22))
            self.ping_status = result == 0
            self.last_ping = datetime.now()
            self.save(update_fields=['ping_status', 'last_ping'])
            return self.ping_status
        except:
            self.ping_status = False
            self.last_ping = datetime.now()
            self.save(update_fields=['ping_status', 'last_ping'])
            return False

class Application(BaseModel):
    """Uygulama modeli"""
    APPLICATION_TYPES = [
        ('jboss', 'JBoss'),
        ('websphere', 'WebSphere'),
        ('openshift', 'OpenShift'),
        ('nginx', 'Nginx'),
        ('apache', 'Apache HTTP Server'),
        ('hazelcast', 'Hazelcast'),
        ('tomcat', 'Apache Tomcat'),
        ('other', 'Diğer'),
    ]
    
    STATUS_CHOICES = [
        ('running', 'Çalışıyor'),
        ('stopped', 'Durduruldu'),
        ('error', 'Hatalı'),
        ('maintenance', 'Bakımda'),
        ('unknown', 'Bilinmiyor'),
    ]
    
    MIGRATION_STATUS_CHOICES = [
        ('not_started', 'Başlanmadı'),
        ('in_progress', 'Devam Ediyor'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('cancelled', 'İptal Edildi'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Uygulama Adı")
    application_type = models.CharField(max_length=20, choices=APPLICATION_TYPES, verbose_name="Uygulama Tipi")
    version = models.CharField(max_length=50, verbose_name="Versiyon")
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='applications', verbose_name="Sunucu")
    port = models.PositiveIntegerField(verbose_name="Port")
    context_path = models.CharField(max_length=200, blank=True, verbose_name="Context Path")
    config_path = models.CharField(max_length=500, verbose_name="Konfigürasyon Yolu")
    log_path = models.CharField(max_length=500, verbose_name="Log Yolu")
    startup_script = models.CharField(max_length=500, blank=True, verbose_name="Başlatma Script'i")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    
    # Durum ve monitoring
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown', verbose_name="Durum")
    last_check = models.DateTimeField(null=True, blank=True, verbose_name="Son Kontrol")
    response_time = models.FloatField(null=True, blank=True, verbose_name="Yanıt Süresi (ms)")
    
    # Migrasyon bilgileri
    migration_status = models.CharField(max_length=20, choices=MIGRATION_STATUS_CHOICES, 
                                      default='not_started', verbose_name="Migrasyon Durumu")
    target_version = models.CharField(max_length=50, blank=True, verbose_name="Hedef Versiyon")
    migration_date = models.DateField(null=True, blank=True, verbose_name="Migrasyon Tarihi")
    migration_notes = models.TextField(blank=True, verbose_name="Migrasyon Notları")
    
    # Sertifika ve güvenlik
    ssl_enabled = models.BooleanField(default=False, verbose_name="SSL Aktif")
    certificate_expiry = models.DateField(null=True, blank=True, verbose_name="Sertifika Bitiş Tarihi")
    
    # İş kritikliği
    CRITICALITY_CHOICES = [
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik'),
    ]
    criticality = models.CharField(max_length=10, choices=CRITICALITY_CHOICES, 
                                 default='medium', verbose_name="İş Kritikliği")
    
    # Bakım penceresi
    maintenance_window = models.CharField(max_length=100, blank=True, verbose_name="Bakım Penceresi")
    
    class Meta:
        verbose_name = "Uygulama"
        verbose_name_plural = "Uygulamalar"
        ordering = ['name']
        unique_together = ['server', 'port']

    def __str__(self):
        return f"{self.name} ({self.application_type}) - {self.server.hostname}"

    @property
    def full_url(self):
        """Uygulamanın tam URL'si"""
        protocol = 'https' if self.ssl_enabled else 'http'
        return f"{protocol}://{self.server.hostname}:{self.port}{self.context_path}"
    
    @property
    def status_color(self):
        """Durum rengi"""
        colors = {
            'running': 'success',
            'stopped': 'secondary',
            'error': 'danger',
            'maintenance': 'warning',
            'unknown': 'info'
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def migration_status_color(self):
        """Migrasyon durum rengi"""
        colors = {
            'not_started': 'secondary',
            'in_progress': 'warning',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'dark'
        }
        return colors.get(self.migration_status, 'secondary')
    
    @property
    def criticality_color(self):
        """Kritiklik rengi"""
        colors = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger',
            'critical': 'dark'
        }
        return colors.get(self.criticality, 'secondary')
    
    @property
    def is_jboss8(self):
        """JBoss 8 kontrolü"""
        return (self.application_type == 'jboss' and 
                ('8' in self.version or 'EAP 8' in self.version or 'jboss8' in self.version.lower()))
    
    def check_status(self):
        """Uygulama durumunu kontrol et"""
        try:
            import requests
            from datetime import datetime
            
            url = self.full_url
            start_time = datetime.now()
            
            response = requests.get(url, timeout=10, verify=False)
            end_time = datetime.now()
            
            self.response_time = (end_time - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                self.status = 'running'
            else:
                self.status = 'error'
                
            self.last_check = datetime.now()
            self.save(update_fields=['status', 'response_time', 'last_check'])
            return True
            
        except requests.exceptions.ConnectionError:
            self.status = 'stopped'
            self.last_check = datetime.now()
            self.save(update_fields=['status', 'last_check'])
            return False
        except:
            self.status = 'unknown'
            self.last_check = datetime.now()
            self.save(update_fields=['status', 'last_check'])
            return False

class OperationHistory(BaseModel):
    """Operasyon geçmişi"""
    OPERATION_TYPES = [
        ('start', 'Başlatma'),
        ('stop', 'Durdurma'),
        ('restart', 'Yeniden Başlatma'),
        ('deploy', 'Deployment'),
        ('config_change', 'Konfigürasyon Değişikliği'),
        ('maintenance', 'Bakım'),
        ('migration', 'Migrasyon'),
        ('other', 'Diğer'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Başarılı'),
        ('failed', 'Başarısız'),
        ('in_progress', 'Devam Ediyor'),
    ]
    
    application = models.ForeignKey(Application, on_delete=models.CASCADE, 
                                  related_name='operation_history', verbose_name="Uygulama")
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name="İşlem Tipi")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="Durum")
    description = models.TextField(verbose_name="Açıklama")
    executed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name="Yürüten")
    execution_time = models.DateTimeField(auto_now_add=True, verbose_name="Yürütme Zamanı")
    duration = models.DurationField(null=True, blank=True, verbose_name="Süre")
    
    class Meta:
        verbose_name = "Operasyon Geçmişi"
        verbose_name_plural = "Operasyon Geçmişleri"
        ordering = ['-execution_time']
    
    def __str__(self):
        return f"{self.application.name} - {self.get_operation_type_display()}"
    
    @property
    def status_color(self):
        colors = {
            'success': 'success',
            'failed': 'danger',
            'in_progress': 'warning'
        }
        return colors.get(self.status, 'secondary')

class Certificate(BaseModel):
    """Sertifika modeli"""
    CERT_TYPES = [
        ('ssl', 'SSL/TLS'),
        ('code_signing', 'Code Signing'),
        ('client', 'Client Certificate'),
        ('ca', 'Certificate Authority'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Sertifika Adı")
    cert_type = models.CharField(max_length=20, choices=CERT_TYPES, verbose_name="Sertifika Tipi")
    application = models.ForeignKey(Application, on_delete=models.CASCADE, 
                                  related_name='certificates', verbose_name="Uygulama")
    issuer = models.CharField(max_length=200, verbose_name="Veren Kurum")
    subject = models.CharField(max_length=200, verbose_name="Konu")
    serial_number = models.CharField(max_length=100, verbose_name="Seri Numarası")
    issue_date = models.DateField(verbose_name="Veriliş Tarihi")
    expiry_date = models.DateField(verbose_name="Bitiş Tarihi")
    fingerprint = models.CharField(max_length=200, blank=True, verbose_name="Parmak İzi")
    
    class Meta:
        verbose_name = "Sertifika"
        verbose_name_plural = "Sertifikalar"
        ordering = ['expiry_date']
    
    def __str__(self):
        return f"{self.name} - {self.application.name}"
    
    @property
    def days_until_expiry(self):
        """Bitiş tarihine kalan gün sayısı"""
        from django.utils import timezone
        return (self.expiry_date - timezone.now().date()).days
    
    @property
    def is_expiring_soon(self):
        """30 gün içinde bitiyor mu?"""
        return self.days_until_expiry <= 30
    
    @property
    def is_expired(self):
        """Süresi dolmuş mu?"""
        return self.days_until_expiry < 0
    
    @property
    def status_color(self):
        """Durum rengi"""
        if self.is_expired:
            return 'danger'
        elif self.is_expiring_soon:
            return 'warning'
        else:
            return 'success'
