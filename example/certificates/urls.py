from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    # Ana sayfalar
    path('', views.CertificateOverviewView.as_view(), name='overview'),
    
    # KDB Sertifikaları
    path('kdb/', views.KdbCertificateListView.as_view(), name='kdb_list'),
    path('kdb/<int:pk>/', views.KdbCertificateDetailView.as_view(), name='kdb_detail'),
    
    # Java Sertifikaları
    path('java/', views.JavaCertificateListView.as_view(), name='java_list'),
    path('java/<int:pk>/', views.JavaCertificateDetailView.as_view(), name='java_detail'),
    
    # API Endpoints
    path('api/stats/', views.certificate_stats_api, name='certificate_stats_api'),
    path('api/expiring/', views.expiring_certificates_api, name='expiring_certificates_api'),
    
    # Yönetim
    path('sync/', views.trigger_sync, name='trigger_sync'),
    path('export/', views.export_certificates, name='export_certificates'),
    path('notifications/', views.NotificationSettingsView.as_view(), name='notification_settings'),
    path('logs/', views.SyncLogView.as_view(), name='sync_logs'),
]
