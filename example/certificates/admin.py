from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    KdbCertificate, JavaCertificate, CertificateAlert,
    CertificateNotificationSettings, CertificateSyncLog
)

@admin.register(KdbCertificate)
class KdbCertificateAdmin(admin.ModelAdmin):
    list_display = [
        'common_name', 'data_source', 'valid_to', 'days_until_expiry_display',
        'expiry_status_badge', 'server_count', 'is_active'
    ]
    list_filter = [
        'data_source', 'certificate_type', 'is_active', 'is_self_signed',
        'is_wildcard', 'created_at'
    ]
    search_fields = [
        'common_name', 'subject', 'issuer', 'serial_number',
        'servers__hostname', 'applications__name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'last_checked', 'days_until_expiry',
        'expiry_status', 'fingerprint_sha1', 'fingerprint_sha256'
    ]
    filter_horizontal = ['servers', 'applications']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('common_name', 'certificate_type', 'data_source', 'is_active')
        }),
        ('Sertifika Detayları', {
            'fields': (
                'subject', 'issuer', 'serial_number', 'algorithm', 'key_size',
                'fingerprint_sha1', 'fingerprint_sha256'
            )
        }),
        ('Geçerlilik', {
            'fields': ('valid_from', 'valid_to', 'days_until_expiry', 'expiry_status')
        }),
        ('KDB Özel Alanları', {
            'fields': (
                'kdb_file_path', 'password_stash', 'appviewx_cert_id',
                'appviewx_status', 'ihs_server', 'virtual_host'
            )
        }),
        ('İlişkiler', {
            'fields': ('servers', 'applications')
        }),
        ('Sistem Bilgileri', {
            'fields': ('created_at', 'updated_at', 'last_checked'),
            'classes': ('collapse',)
        }),
    )
    
    def days_until_expiry_display(self, obj):
        days = obj.days_until_expiry
        if days < 0:
            return format_html('<span style="color: red;">Süresi doldu ({} gün)</span>', abs(days))
        elif days <= 7:
            return format_html('<span style="color: red;">{} gün</span>', days)
        elif days <= 30:
            return format_html('<span style="color: orange;">{} gün</span>', days)
        else:
            return format_html('<span style="color: green;">{} gün</span>', days)
    days_until_expiry_display.short_description = 'Kalan Gün'
    
    def expiry_status_badge(self, obj):
        color_map = {
            'expired': 'red',
            'critical': 'red',
            'warning': 'orange',
            'valid': 'green'
        }
        color = color_map.get(obj.expiry_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.expiry_status_display
        )
    expiry_status_badge.short_description = 'Durum'
    
    def server_count(self, obj):
        count = obj.servers.count()
        if count > 0:
            return format_html('<a href="{}?certificates__id={}">{} sunucu</a>',
                             reverse('admin:inventory_server_changelist'), obj.id, count)
        return '0 sunucu'
    server_count.short_description = 'Sunucular'

@admin.register(JavaCertificate)
class JavaCertificateAdmin(admin.ModelAdmin):
    list_display = [
        'common_name', 'alias', 'keystore_type', 'valid_to',
        'days_until_expiry_display', 'expiry_status_badge', 'server_count', 'is_active'
    ]
    list_filter = [
        'keystore_type', 'certificate_type', 'is_active', 'is_self_signed',
        'is_wildcard', 'created_at'
    ]
    search_fields = [
        'common_name', 'alias', 'keystore_path', 'subject', 'issuer',
        'serial_number', 'servers__hostname'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'last_checked', 'days_until_expiry',
        'expiry_status', 'keystore_size', 'keystore_modified'
    ]
    filter_horizontal = ['servers', 'applications']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('common_name', 'alias', 'certificate_type', 'is_active')
        }),
        ('Keystore Bilgileri', {
            'fields': (
                'keystore_path', 'keystore_type', 'keystore_size',
                'keystore_modified', 'java_version'
            )
        }),
        ('Sertifika Detayları', {
            'fields': (
                'subject', 'issuer', 'serial_number', 'algorithm', 'key_size'
            )
        }),
        ('Geçerlilik', {
            'fields': ('valid_from', 'valid_to', 'days_until_expiry', 'expiry_status')
        }),
        ('İlişkiler', {
            'fields': ('servers', 'applications')
        }),
        ('Sistem Bilgileri', {
            'fields': ('created_at', 'updated_at', 'last_checked'),
            'classes': ('collapse',)
        }),
    )
    
    def days_until_expiry_display(self, obj):
        days = obj.days_until_expiry
        if days < 0:
            return format_html('<span style="color: red;">Süresi doldu ({} gün)</span>', abs(days))
        elif days <= 7:
            return format_html('<span style="color: red;">{} gün</span>', days)
        elif days <= 30:
            return format_html('<span style="color: orange;">{} gün</span>', days)
        else:
            return format_html('<span style="color: green;">{} gün</span>', days)
    days_until_expiry_display.short_description = 'Kalan Gün'
    
    def expiry_status_badge(self, obj):
        color_map = {
            'expired': 'red',
            'critical': 'red',
            'warning': 'orange',
            'valid': 'green'
        }
        color = color_map.get(obj.expiry_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.expiry_status_display
        )
    expiry_status_badge.short_description = 'Durum'
    
    def server_count(self, obj):
        count = obj.servers.count()
        if count > 0:
            return format_html('<a href="{}?certificates__id={}">{} sunucu</a>',
                             reverse('admin:inventory_server_changelist'), obj.id, count)
        return '0 sunucu'
    server_count.short_description = 'Sunucular'

@admin.register(CertificateAlert)
class CertificateAlertAdmin(admin.ModelAdmin):
    list_display = [
        'certificate_info', 'alert_type', 'status_badge', 'sent_at',
        'retry_count', 'created_at'
    ]
    list_filter = ['alert_type', 'status', 'created_at', 'sent_at']
    search_fields = ['certificate_id', 'recipients', 'error_message']
    readonly_fields = ['created_at', 'updated_at', 'sent_at']
    
    def certificate_info(self, obj):
        cert = obj.get_certificate()
        if cert:
            return f"{obj.certificate_type.upper()}: {cert.common_name}"
        return f"{obj.certificate_type.upper()} #{obj.certificate_id}"
    certificate_info.short_description = 'Sertifika'
    
    def status_badge(self, obj):
        color_map = {
            'pending': 'orange',
            'sent': 'green',
            'failed': 'red',
            'acknowledged': 'blue'
        }
        color = color_map.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Durum'

@admin.register(CertificateNotificationSettings)
class CertificateNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'email_enabled', 'check_frequency', 'last_check', 'is_active']
    list_filter = ['email_enabled', 'is_active', 'check_frequency']
    search_fields = ['name', 'email_recipients']
    
    fieldsets = (
        ('Temel Ayarlar', {
            'fields': ('name', 'is_active')
        }),
        ('Bildirim Zamanları', {
            'fields': ('warning_days', 'check_frequency', 'last_check')
        }),
        ('E-posta Ayarları', {
            'fields': ('email_enabled', 'email_recipients', 'email_template')
        }),
        ('Filtreler', {
            'fields': ('certificate_types', 'environments', 'criticality_levels'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CertificateSyncLog)
class CertificateSyncLogAdmin(admin.ModelAdmin):
    list_display = [
        'sync_type', 'status_badge', 'started_at', 'duration_display',
        'success_rate_display', 'total_processed'
    ]
    list_filter = ['sync_type', 'status', 'started_at']
    search_fields = ['error_details']
    readonly_fields = [
        'started_at', 'completed_at', 'duration', 'total_processed',
        'total_created', 'total_updated', 'total_errors', 'success_rate'
    ]
    
    fieldsets = (
        ('Senkronizasyon Bilgileri', {
            'fields': ('sync_type', 'status', 'started_at', 'completed_at', 'duration')
        }),
        ('İstatistikler', {
            'fields': (
                'total_processed', 'total_created', 'total_updated',
                'total_errors', 'success_rate'
            )
        }),
        ('Detaylar', {
            'fields': ('log_details', 'error_details'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        color_map = {
            'running': 'blue',
            'completed': 'green',
            'failed': 'red',
            'partial': 'orange'
        }
        color = color_map.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Durum'
    
    def duration_display(self, obj):
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        return "-"
    duration_display.short_description = 'Süre'
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        if rate >= 95:
            color = 'green'
        elif rate >= 80:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">%{}</span>',
            color, rate
        )
    success_rate_display.short_description = 'Başarı Oranı'
