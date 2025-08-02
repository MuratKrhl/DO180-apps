from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.utils import timezone
from authentication.models import UserSession
from datetime import timedelta

class Command(BaseCommand):
    help = 'Süresi dolmuş oturumları temizle'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Kaç gün önceki oturumları temizle (varsayılan: 7)',
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Django sessions
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        session_count = expired_sessions.count()
        expired_sessions.delete()
        
        # User sessions
        old_user_sessions = UserSession.objects.filter(last_activity__lt=cutoff_date)
        user_session_count = old_user_sessions.count()
        old_user_sessions.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Temizlendi: {session_count} Django oturumu, {user_session_count} kullanıcı oturumu'
            )
        )
