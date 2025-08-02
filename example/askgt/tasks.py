from celery import shared_task
from django.utils import timezone
from .services import DocumentSyncService
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def sync_documents_task(self):
    """Doküman senkronizasyon görevi"""
    try:
        sync_service = DocumentSyncService()
        results = sync_service.sync_all_sources()
        
        total_synced = sum(results.values())
        logger.info(f"Document sync completed: {total_synced} documents synced")
        
        return {
            'status': 'success',
            'total_synced': total_synced,
            'results': results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Document sync failed: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying document sync (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {
            'status': 'failed',
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }

@shared_task
def sync_specific_source_task(source_name: str):
    """Belirli bir kaynağı senkronize et"""
    try:
        from .models import APISource
        source = APISource.objects.get(name=source_name, is_active=True)
        
        sync_service = DocumentSyncService()
        count = sync_service.sync_from_source(source)
        
        logger.info(f"Synced {count} documents from {source_name}")
        
        return {
            'status': 'success',
            'source': source_name,
            'synced_count': count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to sync from {source_name}: {str(exc)}")
        return {
            'status': 'failed',
            'source': source_name,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }

@shared_task
def cleanup_old_access_logs():
    """Eski erişim loglarını temizle"""
    try:
        from .models import DocumentAccess
        from datetime import timedelta
        
        # 6 ay öncesinden eski logları sil
        cutoff_date = timezone.now() - timedelta(days=180)
        deleted_count = DocumentAccess.objects.filter(accessed_at__lt=cutoff_date).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old access logs")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to cleanup access logs: {str(exc)}")
        return {
            'status': 'failed',
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }
