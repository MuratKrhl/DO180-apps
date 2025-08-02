from django.core.management.base import BaseCommand
from django.utils import timezone
from certificates.services import NotificationService

class Command(BaseCommand):
    help = 'Süresi yaklaşan sertifikaları kontrol et ve bildirim gönder'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            help='Belirli gün sayısı için kontrol et'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece listele, bildirim gönderme'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Daha önce gönderilmiş olsa bile bildirim gönder'
        )
    
    def handle(self, *args, **options):
        days = options.get('days')
        dry_run = options['dry_run']
        force = options['force']
        
        if dry_run:
            self.stdout.write('DRY RUN: Süresi yaklaşan sertifikalar listeleniyor...')
            
            from certificates.models import KdbCertificate, JavaCertificate
            from datetime import timedelta
            
            now = timezone.now()
            
            if days:
                end_date = now + timedelta(days=days)
                kdb_certs = KdbCertificate.objects.filter(
                    is_active=True,
                    valid_to__gte=now,
                    valid_to__lte=end_date
                ).order_by('valid_to')
                
                java_certs = JavaCertificate.objects.filter(
                    is_active=True,
                    valid_to__gte=now,
                    valid_to__lte=end_date
                ).order_by('valid_to')
            else:
                # Varsayılan: 30 gün
                end_date = now + timedelta(days=30)
                kdb_certs = KdbCertificate.objects.filter(
                    is_active=True,
                    valid_to__gte=now,
                    valid_to__lte=end_date
                ).order_by('valid_to')
                
                java_certs = JavaCertificate.objects.filter(
                    is_active=True,
                    valid_to__gte=now,
                    valid_to__lte=end_date
                ).order_by('valid_to')
            
            self.stdout.write(f'\nKDB Sertifikaları ({kdb_certs.count()} adet):')
            for cert in kdb_certs:
                self.stdout.write(
                    f'  • {cert.common_name} - {cert.valid_to.strftime("%d.%m.%Y")} '
                    f'({cert.days_until_expiry} gün kaldı)'
                )
            
            self.stdout.write(f'\nJava Sertifikaları ({java_certs.count()} adet):')
            for cert in java_certs:
                self.stdout.write(
                    f'  • {cert.common_name} - {cert.valid_to.strftime("%d.%m.%Y")} '
                    f'({cert.days_until_expiry} gün kaldı)'
                )
            
            return
        
        self.stdout.write('Süresi yaklaşan sertifikalar kontrol ediliyor...')
        
        try:
            NotificationService.check_expiring_certificates()
            self.stdout.write(
                self.style.SUCCESS('Sertifika kontrolleri tamamlandı ve bildirimler gönderildi.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Bildirim gönderme hatası: {str(e)}')
            )
