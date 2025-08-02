from django.core.management.base import BaseCommand
from django.conf import settings
from certificates.services import CertificateService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'KDB sertifikalarını senkronize et'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['appviewx', 'sql', 'ansible', 'all'],
            default='all',
            help='Senkronizasyon kaynağı'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece test et, değişiklik yapma'
        )
    
    def handle(self, *args, **options):
        source = options['source']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN modu - değişiklik yapılmayacak')
            )
        
        try:
            if source in ['appviewx', 'all']:
                self.stdout.write('AppViewX senkronizasyonu başlatılıyor...')
                if not dry_run:
                    sync_log = CertificateService.sync_kdb_from_appviewx()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'AppViewX senkronizasyonu tamamlandı: '
                            f'{sync_log.successful_count}/{sync_log.total_processed} başarılı'
                        )
                    )
                else:
                    self.stdout.write('AppViewX senkronizasyonu (DRY RUN)')
            
            if source in ['sql', 'all']:
                self.stdout.write('SQL veritabanı senkronizasyonu başlatılıyor...')
                if not dry_run:
                    sync_log = CertificateService.sync_kdb_from_sql_database()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'SQL senkronizasyonu tamamlandı: '
                            f'{sync_log.successful_count}/{sync_log.total_processed} başarılı'
                        )
                    )
                else:
                    self.stdout.write('SQL senkronizasyonu (DRY RUN)')
            
            if source in ['ansible', 'all']:
                self.stdout.write('Ansible senkronizasyonu henüz implement edilmedi')
            
            self.stdout.write(
                self.style.SUCCESS('KDB sertifika senkronizasyonu tamamlandı!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Senkronizasyon hatası: {e}')
            )
            logger.error(f'KDB senkronizasyon hatası: {e}')
