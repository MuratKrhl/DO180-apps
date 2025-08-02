from celery import shared_task
from django.utils import timezone
from .services import CertificateService, NotificationService
from .models import CertificateSyncLog

@shared_task(bind=True)
def sync_certificates(self, sync_type):
    """Sertifika senkronizasyon task'ı"""
    try:
        if sync_type == 'kdb_appviewx':
            return CertificateService.sync_kdb_from_appviewx()
        elif sync_type == 'kdb_sql':
            return CertificateService.sync_kdb_from_sql()
        elif sync_type == 'java_keystore':
            # Tüm sunucular için Java sertifikalarını senkronize et
            from inventory.models import Server
            servers = Server.objects.filter(is_active=True, operating_system='linux')
            
            for server in servers:
                server_info = {
                    'hostname': server.ip_address,
                    'username': 'middleware',  # settings'ten alınabilir
                    'key_file': '/path/to/ssh/key',  # settings'ten alınabilir
                }
                CertificateService.sync_java_certificates_from_keystore(server_info)
        
    except Exception as e:
        # Task başarısız oldu
        self.retry(countdown=300, max_retries=3)  # 5 dakika sonra tekrar dene

@shared_task
def check_expiring_certificates():
    """Süresi yaklaşan sertifikaları kontrol et"""
    NotificationService.check_expiring_certificates()

@shared_task
def send_weekly_certificate_report():
    """Haftalık sertifika raporu gönder"""
    NotificationService.send_certificate_summary_report()

@shared_task
def cleanup_old_alerts():
    """Eski uyarıları temizle"""
    from datetime import timedelta
    from django.utils import timezone
    from .models import CertificateAlert
    
    # 90 günden eski uyarıları sil
    cutoff_date = timezone.now() - timedelta(days=90)
    deleted_count = CertificateAlert.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    return f"Temizlenen uyarı sayısı: {deleted_count}"
