from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, TemplateView
from django.core.paginator import Paginator
from django.db.models import Q, Count, Case, When, IntegerField
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta, datetime
import json
import csv

from .models import (
    KdbCertificate, JavaCertificate, CertificateAlert, 
    CertificateNotificationSettings, CertificateSyncLog
)
from .forms import CertificateFilterForm, NotificationSettingsForm
from .services import CertificateService, NotificationService

class CertificateOverviewView(LoginRequiredMixin, TemplateView):
    """Sertifika genel bakış sayfası"""
    template_name = 'certificates/overview.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Cache anahtarı
        cache_key = f"certificate_overview_{self.request.user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            context.update(cached_data)
        else:
            # İstatistikleri topla
            overview_data = self.collect_overview_data()
            cache.set(cache_key, overview_data, 300)  # 5 dakika cache
            context.update(overview_data)
        
        return context
    
    def collect_overview_data(self):
        """Genel bakış verilerini topla"""
        now = timezone.now()
        today = now.date()
        
        # KDB İstatistikleri
        kdb_stats = {
            'total': KdbCertificate.objects.filter(is_active=True).count(),
            'expired': KdbCertificate.objects.filter(
                is_active=True, valid_to__lt=now
            ).count(),
            'expiring_30': KdbCertificate.objects.filter(
                is_active=True, 
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=30)
            ).count(),
            'expiring_7': KdbCertificate.objects.filter(
                is_active=True,
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=7)
            ).count(),
        }
        
        # Java İstatistikleri
        java_stats = {
            'total': JavaCertificate.objects.filter(is_active=True).count(),
            'expired': JavaCertificate.objects.filter(
                is_active=True, valid_to__lt=now
            ).count(),
            'expiring_30': JavaCertificate.objects.filter(
                is_active=True,
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=30)
            ).count(),
            'expiring_7': JavaCertificate.objects.filter(
                is_active=True,
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=7)
            ).count(),
        }
        
        # Yaklaşan süreler (Dashboard widget için)
        expiring_certificates = []
        
        # KDB sertifikaları
        kdb_expiring = KdbCertificate.objects.filter(
            is_active=True,
            valid_to__gte=now,
            valid_to__lte=now + timedelta(days=30)
        ).order_by('valid_to')[:10]
        
        for cert in kdb_expiring:
            expiring_certificates.append({
                'type': 'KDB',
                'common_name': cert.common_name,
                'valid_to': cert.valid_to,
                'days_until_expiry': cert.days_until_expiry,
                'expiry_status': cert.expiry_status,
                'expiry_status_color': cert.expiry_status_color,
                'url': f'/certificates/kdb/{cert.id}/',
                'servers': [server.hostname for server in cert.servers.all()[:3]]
            })
        
        # Java sertifikaları
        java_expiring = JavaCertificate.objects.filter(
            is_active=True,
            valid_to__gte=now,
            valid_to__lte=now + timedelta(days=30)
        ).order_by('valid_to')[:10]
        
        for cert in java_expiring:
            expiring_certificates.append({
                'type': 'Java',
                'common_name': cert.common_name,
                'valid_to': cert.valid_to,
                'days_until_expiry': cert.days_until_expiry,
                'expiry_status': cert.expiry_status,
                'expiry_status_color': cert.expiry_status_color,
                'url': f'/certificates/java/{cert.id}/',
                'servers': [server.hostname for server in cert.servers.all()[:3]]
            })
        
        # Tarihe göre sırala
        expiring_certificates.sort(key=lambda x: x['valid_to'])
        
        # Son senkronizasyon logları
        recent_sync_logs = CertificateSyncLog.objects.all()[:5]
        
        # Aktif uyarılar
        active_alerts = CertificateAlert.objects.filter(
            status__in=['pending', 'failed']
        ).count()
        
        return {
            'kdb_stats': kdb_stats,
            'java_stats': java_stats,
            'expiring_certificates': expiring_certificates[:15],
            'recent_sync_logs': recent_sync_logs,
            'active_alerts': active_alerts,
            'total_certificates': kdb_stats['total'] + java_stats['total'],
            'total_expired': kdb_stats['expired'] + java_stats['expired'],
            'total_expiring_30': kdb_stats['expiring_30'] + java_stats['expiring_30'],
            'total_expiring_7': kdb_stats['expiring_7'] + java_stats['expiring_7'],
        }

class KdbCertificateListView(LoginRequiredMixin, ListView):
    """KDB Sertifikaları listesi"""
    model = KdbCertificate
    template_name = 'certificates/kdb_certificate_list.html'
    context_object_name = 'certificates'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = KdbCertificate.objects.filter(is_active=True).select_related().prefetch_related('servers', 'applications')
        
        # Filtreleme parametreleri
        search = self.request.GET.get('search')
        data_source = self.request.GET.get('data_source')
        expiry_status = self.request.GET.get('expiry_status')
        server_id = self.request.GET.get('server')
        
        if search:
            queryset = queryset.filter(
                Q(common_name__icontains=search) |
                Q(subject__icontains=search) |
                Q(issuer__icontains=search) |
                Q(serial_number__icontains=search) |
                Q(servers__hostname__icontains=search)
            ).distinct()
        
        if data_source:
            queryset = queryset.filter(data_source=data_source)
        
        if server_id:
            queryset = queryset.filter(servers__id=server_id)
        
        # Bitiş durumu filtresi
        now = timezone.now()
        if expiry_status == 'expired':
            queryset = queryset.filter(valid_to__lt=now)
        elif expiry_status == 'expiring_7':
            queryset = queryset.filter(
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=7)
            )
        elif expiry_status == 'expiring_30':
            queryset = queryset.filter(
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=30)
            )
        elif expiry_status == 'valid':
            queryset = queryset.filter(valid_to__gt=now + timedelta(days=30))
        
        # Sıralama
        sort_by = self.request.GET.get('sort', 'valid_to')
        if sort_by in ['valid_to', '-valid_to', 'common_name', '-common_name', 'created_at', '-created_at']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtreleme formu
        context['filter_form'] = CertificateFilterForm(self.request.GET)
        
        # Filtreleme seçenekleri
        context['data_source_choices'] = KdbCertificate.SOURCE_CHOICES
        context['servers'] = KdbCertificate.objects.filter(is_active=True).values_list(
            'servers__id', 'servers__hostname'
        ).distinct()
        
        # Aktif filtreler
        context['active_filters'] = {
            'search': self.request.GET.get('search', ''),
            'data_source': self.request.GET.get('data_source', ''),
            'expiry_status': self.request.GET.get('expiry_status', ''),
            'server': self.request.GET.get('server', ''),
        }
        
        # İstatistikler
        now = timezone.now()
        context['stats'] = {
            'total': self.get_queryset().count(),
            'expired': self.get_queryset().filter(valid_to__lt=now).count(),
            'expiring_30': self.get_queryset().filter(
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=30)
            ).count(),
        }
        
        return context

class JavaCertificateListView(LoginRequiredMixin, ListView):
    """Java Sertifikaları listesi"""
    model = JavaCertificate
    template_name = 'certificates/java_certificate_list.html'
    context_object_name = 'certificates'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = JavaCertificate.objects.filter(is_active=True).select_related().prefetch_related('servers', 'applications')
        
        # Filtreleme parametreleri
        search = self.request.GET.get('search')
        keystore_type = self.request.GET.get('keystore_type')
        expiry_status = self.request.GET.get('expiry_status')
        server_id = self.request.GET.get('server')
        
        if search:
            queryset = queryset.filter(
                Q(common_name__icontains=search) |
                Q(alias__icontains=search) |
                Q(keystore_path__icontains=search) |
                Q(servers__hostname__icontains=search)
            ).distinct()
        
        if keystore_type:
            queryset = queryset.filter(keystore_type=keystore_type)
        
        if server_id:
            queryset = queryset.filter(servers__id=server_id)
        
        # Bitiş durumu filtresi
        now = timezone.now()
        if expiry_status == 'expired':
            queryset = queryset.filter(valid_to__lt=now)
        elif expiry_status == 'expiring_7':
            queryset = queryset.filter(
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=7)
            )
        elif expiry_status == 'expiring_30':
            queryset = queryset.filter(
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=30)
            )
        elif expiry_status == 'valid':
            queryset = queryset.filter(valid_to__gt=now + timedelta(days=30))
        
        # Sıralama
        sort_by = self.request.GET.get('sort', 'valid_to')
        if sort_by in ['valid_to', '-valid_to', 'common_name', '-common_name', 'alias', '-alias']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtreleme seçenekleri
        context['keystore_type_choices'] = JavaCertificate.KEYSTORE_TYPES
        context['servers'] = JavaCertificate.objects.filter(is_active=True).values_list(
            'servers__id', 'servers__hostname'
        ).distinct()
        
        # Aktif filtreler
        context['active_filters'] = {
            'search': self.request.GET.get('search', ''),
            'keystore_type': self.request.GET.get('keystore_type', ''),
            'expiry_status': self.request.GET.get('expiry_status', ''),
            'server': self.request.GET.get('server', ''),
        }
        
        # İstatistikler
        now = timezone.now()
        context['stats'] = {
            'total': self.get_queryset().count(),
            'expired': self.get_queryset().filter(valid_to__lt=now).count(),
            'expiring_30': self.get_queryset().filter(
                valid_to__gte=now,
                valid_to__lte=now + timedelta(days=30)
            ).count(),
        }
        
        return context

class KdbCertificateDetailView(LoginRequiredMixin, DetailView):
    """KDB Sertifika detay sayfası"""
    model = KdbCertificate
    template_name = 'certificates/kdb_certificate_detail.html'
    context_object_name = 'certificate'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        certificate = self.get_object()
        
        # İlgili uyarılar
        context['alerts'] = CertificateAlert.objects.filter(
            certificate_type='kdb',
            certificate_id=certificate.id
        ).order_by('-created_at')[:10]
        
        # Benzer sertifikalar (aynı issuer)
        context['similar_certificates'] = KdbCertificate.objects.filter(
            issuer=certificate.issuer,
            is_active=True
        ).exclude(id=certificate.id)[:5]
        
        # Sertifika zinciri bilgisi (eğer varsa)
        context['certificate_chain'] = self.get_certificate_chain(certificate)
        
        return context
    
    def get_certificate_chain(self, certificate):
        """Sertifika zinciri bilgisini getir"""
        # Bu method gerçek implementasyonda sertifika zincirini analiz edecek
        return []

class JavaCertificateDetailView(LoginRequiredMixin, DetailView):
    """Java Sertifika detay sayfası"""
    model = JavaCertificate
    template_name = 'certificates/java_certificate_detail.html'
    context_object_name = 'certificate'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        certificate = self.get_object()
        
        # İlgili uyarılar
        context['alerts'] = CertificateAlert.objects.filter(
            certificate_type='java',
            certificate_id=certificate.id
        ).order_by('-created_at')[:10]
        
        # Aynı keystore'daki diğer sertifikalar
        context['keystore_certificates'] = JavaCertificate.objects.filter(
            keystore_path=certificate.keystore_path,
            is_active=True
        ).exclude(id=certificate.id)
        
        # Keytool komut örnekleri
        context['keytool_commands'] = {
            'list': certificate.get_keytool_command(),
            'export': f"keytool -export -keystore {certificate.keystore_path} -alias {certificate.alias} -file {certificate.alias}.crt",
            'delete': f"keytool -delete -keystore {certificate.keystore_path} -alias {certificate.alias}",
        }
        
        return context

# AJAX Views
@login_required
def certificate_stats_api(request):
    """Sertifika istatistikleri API"""
    cache_key = f"certificate_stats_{request.user.id}"
    data = cache.get(cache_key)
    
    if not data:
        view = CertificateOverviewView()
        data = view.collect_overview_data()
        cache.set(cache_key, data, 300)
    
    return JsonResponse(data)

@login_required
def expiring_certificates_api(request):
    """Yaklaşan sertifikalar API (Dashboard widget için)"""
    days = int(request.GET.get('days', 30))
    limit = int(request.GET.get('limit', 10))
    
    now = timezone.now()
    end_date = now + timedelta(days=days)
    
    # KDB ve Java sertifikalarını birleştir
    expiring_certificates = []
    
    # KDB sertifikaları
    kdb_certs = KdbCertificate.objects.filter(
        is_active=True,
        valid_to__gte=now,
        valid_to__lte=end_date
    ).order_by('valid_to')[:limit//2]
    
    for cert in kdb_certs:
        expiring_certificates.append({
            'id': cert.id,
            'type': 'KDB',
            'common_name': cert.common_name,
            'valid_to': cert.valid_to.isoformat(),
            'days_until_expiry': cert.days_until_expiry,
            'expiry_status': cert.expiry_status,
            'expiry_status_color': cert.expiry_status_color,
            'expiry_status_display': cert.expiry_status_display,
            'url': f'/certificates/kdb/{cert.id}/',
            'servers': [server.hostname for server in cert.servers.all()[:2]]
        })
    
    # Java sertifikaları
    java_certs = JavaCertificate.objects.filter(
        is_active=True,
        valid_to__gte=now,
        valid_to__lte=end_date
    ).order_by('valid_to')[:limit//2]
    
    for cert in java_certs:
        expiring_certificates.append({
            'id': cert.id,
            'type': 'Java',
            'common_name': cert.common_name,
            'valid_to': cert.valid_to.isoformat(),
            'days_until_expiry': cert.days_until_expiry,
            'expiry_status': cert.expiry_status,
            'expiry_status_color': cert.expiry_status_color,
            'expiry_status_display': cert.expiry_status_display,
            'url': f'/certificates/java/{cert.id}/',
            'servers': [server.hostname for server in cert.servers.all()[:2]]
        })
    
    # Tarihe göre sırala ve limit uygula
    expiring_certificates.sort(key=lambda x: x['valid_to'])
    expiring_certificates = expiring_certificates[:limit]
    
    return JsonResponse({
        'certificates': expiring_certificates,
        'total_count': len(expiring_certificates)
    })

@permission_required('certificates.add_certificatesynclog')
def trigger_sync(request):
    """Manuel senkronizasyon tetikleme"""
    if request.method == 'POST':
        sync_type = request.POST.get('sync_type')
        
        if sync_type in ['kdb_appviewx', 'kdb_sql', 'java_keystore']:
            # Celery task'ını tetikle
            from .tasks import sync_certificates
            task = sync_certificates.delay(sync_type)
            
            messages.success(request, f'Senkronizasyon başlatıldı. Task ID: {task.id}')
        else:
            messages.error(request, 'Geçersiz senkronizasyon tipi.')
    
    return redirect('certificates:overview')

@login_required
def export_certificates(request):
    """Sertifika dışa aktarma"""
    cert_type = request.GET.get('type', 'all')  # kdb, java, all
    format_type = request.GET.get('format', 'csv')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="certificates_{cert_type}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Tip', 'Common Name', 'Subject', 'Issuer', 'Serial Number',
            'Geçerlilik Başlangıcı', 'Geçerlilik Bitişi', 'Kalan Gün',
            'Durum', 'Sunucular'
        ])
        
        certificates = []
        
        if cert_type in ['kdb', 'all']:
            kdb_certs = KdbCertificate.objects.filter(is_active=True)
            for cert in kdb_certs:
                certificates.append([
                    'KDB', cert.common_name, cert.subject, cert.issuer,
                    cert.serial_number, cert.valid_from.strftime('%d.%m.%Y'),
                    cert.valid_to.strftime('%d.%m.%Y'), cert.days_until_expiry,
                    cert.expiry_status_display,
                    ', '.join([s.hostname for s in cert.servers.all()[:3]])
                ])
        
        if cert_type in ['java', 'all']:
            java_certs = JavaCertificate.objects.filter(is_active=True)
            for cert in java_certs:
                certificates.append([
                    'Java', cert.common_name, cert.subject, cert.issuer,
                    cert.serial_number, cert.valid_from.strftime('%d.%m.%Y'),
                    cert.valid_to.strftime('%d.%m.%Y'), cert.days_until_expiry,
                    cert.expiry_status_display,
                    ', '.join([s.hostname for s in cert.servers.all()[:3]])
                ])
        
        # Bitiş tarihine göre sırala
        certificates.sort(key=lambda x: x[6])  # valid_to index
        
        for cert_data in certificates:
            writer.writerow(cert_data)
        
        return response
    
    return JsonResponse({'error': 'Desteklenmeyen format'})

# Notification Management Views
class NotificationSettingsView(PermissionRequiredMixin, TemplateView):
    """Bildirim ayarları yönetimi"""
    template_name = 'certificates/notification_settings.html'
    permission_required = 'certificates.change_certificatenotificationsettings'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings'] = CertificateNotificationSettings.objects.filter(is_active=True)
        context['recent_alerts'] = CertificateAlert.objects.all()[:10]
        return context

class SyncLogView(LoginRequiredMixin, ListView):
    """Senkronizasyon logları"""
    model = CertificateSyncLog
    template_name = 'certificates/sync_logs.html'
    context_object_name = 'logs'
    paginate_by = 20
    ordering = ['-started_at']
