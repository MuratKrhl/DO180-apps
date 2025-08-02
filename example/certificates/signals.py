from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import KdbCertificate, JavaCertificate, CertificateAlert

@receiver(post_save, sender=KdbCertificate)
@receiver(post_save, sender=JavaCertificate)
def invalidate_certificate_cache(sender, instance, **kwargs):
    """Sertifika değiştiğinde cache'i temizle"""
    cache.delete_pattern('certificate_*')
    cache.delete_pattern('dashboard_*')

@receiver(post_save, sender=CertificateAlert)
def log_certificate_alert(sender, instance, created, **kwargs):
    """Sertifika uyarısı oluşturulduğunda log'la"""
    if created:
        import logging
        logger = logging.getLogger('certificates')
        
        cert = instance.get_certificate()
        if cert:
            logger.info(
                f'Certificate alert created: {instance.get_alert_type_display()} '
                f'for {cert.common_name} (expires: {cert.valid_to})'
            )
