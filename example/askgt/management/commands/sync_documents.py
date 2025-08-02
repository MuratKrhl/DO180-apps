from django.core.management.base import BaseCommand
from django.utils import timezone
from askgt.services import DocumentSyncService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Harici API kaynaklarından dokümanları senkronize et'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            help='Belirli bir kaynağı senkronize et',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece test et, veri kaydetme',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Detaylı çıktı',
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        
        if options['verbose']:
            self.stdout.write(f"Senkronizasyon başlatıldı: {start_time}")
        
        try:
            sync_service = DocumentSyncService()
            
            if options['source']:
                # Belirli kaynak
                from askgt.models import APISource
                try:
                    source = APISource.objects.get(name=options['source'], is_active=True)
                    if not options['dry_run']:
                        count = sync_service.sync_from_source(source)
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ {source.name}: {count} doküman senkronize edildi")
                        )
                    else:
                        self.stdout.write(f"🔍 DRY RUN: {source.name} kaynağı test edilecek")
                        
                except APISource.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Kaynak bulunamadı: {options['source']}")
                    )
                    return
            else:
                # Tüm kaynaklar
                if not options['dry_run']:
                    results = sync_service.sync_all_sources()
                    
                    total_synced = sum(results.values())
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Toplam {total_synced} doküman senkronize edildi")
                    )
                    
                    for source_name, count in results.items():
                        if count > 0:
                            self.stdout.write(f"  📄 {source_name}: {count} doküman")
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"  ⚠️ {source_name}: Senkronizasyon başarısız")
                            )
                else:
                    self.stdout.write("🔍 DRY RUN: Tüm kaynaklar test edilecek")
            
            end_time = timezone.now()
            duration = end_time - start_time
            
            if options['verbose']:
                self.stdout.write(f"Senkronizasyon tamamlandı: {end_time}")
                self.stdout.write(f"Süre: {duration.total_seconds():.2f} saniye")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Senkronizasyon hatası: {str(e)}")
            )
            logger.error(f"Document sync error: {str(e)}", exc_info=True)
