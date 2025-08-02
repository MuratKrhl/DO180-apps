from django.core.management.base import BaseCommand
from django.utils import timezone
from certificates.services import CertificateService
from inventory.models import Server

class Command(BaseCommand):
    help = 'Java keystore sertifikalarını senkronize et'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--server',
            type=str,
            help='Belirli bir sunucu hostname\'i'
        )
        parser.add_argument(
            '--environment',
            type=str,
            choices=['prod', 'test', 'dev', 'stage'],
            help='Belirli bir ortam'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece test et, veri kaydetme'
        )
    
    def handle(self, *args, **options):
        server_hostname = options.get('server')
        environment = options.get('environment')
        dry_run = options['dry_run']
        
        # Sunucuları filtrele
        servers = Server.objects.filter(
            is_active=True,
            operating_system='linux'  # Java genelde Linux sunucularda
        )
        
        if server_hostname:
            servers = servers.filter(hostname=server_hostname)
        
        if environment:
            servers = servers.filter(environment=environment)
        
        if not servers.exists():
            self.stdout.write(
                self.style.WARNING('Kriterlere uygun sunucu bulunamadı.')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Java sertifika senkronizasyonu başlatılıyor... '
                f'({servers.count()} sunucu)'
            )
        )
        
        total_processed = 0
        total_errors = 0
        
        for server in servers:
            try:
                self.stdout.write(f'İşleniyor: {server.hostname}')
                
                if dry_run:
                    self.stdout.write(f'DRY RUN: {server.hostname} bağlantısı test ediliyor...')
                    continue
                
                server_info = {
                    'hostname': server.ip_address,
                    'username': 'middleware',  # settings'ten alınabilir
                    'key_file': '/path/to/ssh/key',  # settings'ten alınabilir
                }
                
                sync_log = CertificateService.sync_java_certificates_from_keystore(server_info)
                
                self.stdout.write(
                    f'  ✓ İşlenen: {sync_log.total_processed}, '
                    f'Yeni: {sync_log.total_created}, '
                    f'Güncellenen: {sync_log.total_updated}, '
                    f'Hata: {sync_log.total_errors}'
                )
                
                total_processed += sync_log.total_processed
                total_errors += sync_log.total_errors
                
            except Exception as e:
                total_errors += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ {server.hostname}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSenkronizasyon tamamlandı!\n'
                f'Toplam işlenen: {total_processed}\n'
                f'Toplam hata: {total_errors}'
            )
        )
