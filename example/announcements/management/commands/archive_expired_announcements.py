from django.core.management.base import BaseCommand
from django.utils import timezone
from announcements.models import Announcement

class Command(BaseCommand):
    help = 'Süresi dolmuş duyuruları arşivle'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Sadece test et, değişiklik yapma'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        expired_announcements = Announcement.objects.filter(
            is_active=True,
            status='published',
            end_date__lt=now
        )
        
        count = expired_announcements.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: {count} duyuru arşivlenecek')
            )
        else:
            expired_announcements.update(status='archived')
            self.stdout.write(
                self.style.SUCCESS(f'{count} duyuru başarıyla arşivlendi')
            )
