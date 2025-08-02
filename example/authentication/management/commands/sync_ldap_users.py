from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django_auth_ldap.backend import LDAPBackend
from authentication.models import UserProfile
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'LDAP kullanıcılarını Django ile senkronize et'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Değişiklikleri kaydetmeden test et',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Belirli bir kullanıcıyı senkronize et',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        username = options.get('username')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - Değişiklikler kaydedilmeyecek'))
        
        backend = LDAPBackend()
        
        if username:
            self.sync_single_user(backend, username, dry_run)
        else:
            self.sync_all_users(backend, dry_run)

    def sync_single_user(self, backend, username, dry_run):
        """Tek kullanıcıyı senkronize et"""
        try:
            # LDAP'dan kullanıcı bilgilerini al
            ldap_user = backend.get_user_model().objects.filter(username=username).first()
            
            if not ldap_user:
                self.stdout.write(
                    self.style.ERROR(f'Kullanıcı bulunamadı: {username}')
                )
                return
            
            # Profil oluştur/güncelle
            if not dry_run:
                profile, created = UserProfile.objects.get_or_create(user=ldap_user)
                profile.last_ldap_sync = timezone.now()
                profile.save()
            
            action = "oluşturuldu" if created else "güncellendi"
            self.stdout.write(
                self.style.SUCCESS(f'Kullanıcı {action}: {username}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Hata ({username}): {str(e)}')
            )

    def sync_all_users(self, backend, dry_run):
        """Tüm LDAP kullanıcılarını senkronize et"""
        # Bu implementasyon LDAP sunucunuza göre özelleştirilmelidir
        self.stdout.write(
            self.style.WARNING('Toplu senkronizasyon için LDAP konfigürasyonu gerekli')
        )

    def create_default_groups(self, dry_run):
        """Varsayılan grupları oluştur"""
        default_groups = ['Admins', 'Users', 'Operators']
        
        for group_name in default_groups:
            if not dry_run:
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Grup oluşturuldu: {group_name}')
                    )
