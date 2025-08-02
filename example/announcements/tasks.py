from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Announcement
import logging

logger = logging.getLogger(__name__)

@shared_task
def auto_archive_expired_announcements():
    """Süresi dolmuş duyuruları otomatik arşivle"""
    now = timezone.now()
    
    expired_announcements = Announcement.objects.filter(
        is_active=True,
        status='published',
        end_date__lt=now
    )
    
    count = 0
    for announcement in expired_announcements:
        announcement.status = 'archived'
        announcement.save(update_fields=['status'])
        count += 1
    
    logger.info(f'{count} duyuru otomatik olarak arşivlendi')
    return f'{count} duyuru arşivlendi'

@shared_task
def auto_publish_scheduled_announcements():
    """Zamanlanmış duyuruları otomatik yayınla"""
    now = timezone.now()
    
    scheduled_announcements = Announcement.objects.filter(
        is_active=True,
        status='scheduled',
        start_date__lte=now
    )
    
    count = 0
    for announcement in scheduled_announcements:
        announcement.status = 'published'
        announcement.save(update_fields=['status'])
        count += 1
    
    logger.info(f'{count} zamanlanmış duyuru yayınlandı')
    return f'{count} duyuru yayınlandı'

@shared_task
def send_announcement_notifications(announcement_id):
    """Yeni duyuru bildirimleri gönder"""
    try:
        announcement = Announcement.objects.get(id=announcement_id)
        
        # E-posta listesi (örnek - gerçek implementasyonda abonelik sisteminden gelecek)
        recipient_list = ['admin@company.com']  # Dinamik olarak belirlenecek
        
        context = {
            'announcement': announcement,
            'site_url': settings.SITE_URL,
        }
        
        subject = f'Yeni Duyuru: {announcement.title}'
        message = render_to_string('announcements/emails/new_announcement.txt', context)
        html_message = render_to_string('announcements/emails/new_announcement.html', context)
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f'Duyuru bildirimi gönderildi: {announcement.title}')
        return 'Bildirim gönderildi'
        
    except Exception as e:
        logger.error(f'Duyuru bildirim hatası: {e}')
        raise
