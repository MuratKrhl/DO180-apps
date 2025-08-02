from django.db import models
from core.models import BaseModel
from inventory.models import Server, Application
import json

class MetricSource(BaseModel):
    """Metrik kaynakları (Dynatrace, Prometheus, Grafana, vb.)"""
    SOURCE_TYPES = [
        ('dynatrace', 'Dynatrace'),
        ('prometheus', 'Prometheus'),
        ('grafana', 'Grafana'),
        ('zabbix', 'Zabbix'),
        ('nagios', 'Nagios'),
        ('splunk', 'Splunk'),
        ('kibana', 'Kibana'),
        ('instana', 'Instana'),
        ('custom_api', 'Özel API'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Kaynak Adı")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, verbose_name="Kaynak Tipi")
    base_url = models.URLField(verbose_name="Base URL")
    api_key = models.CharField(max_length=500, blank=True, verbose_name="API Anahtarı")
    username = models.CharField(max_length=100, blank=True, verbose_name="Kullanıcı Adı")
    password = models.CharField(max_length=100, blank=True, verbose_name="Şifre")
    headers = models.JSONField(default=dict, blank=True, verbose_name="HTTP Headers")
    is_default = models.BooleanField(default=False, verbose_name="Varsayılan Kaynak")
    
    class Meta:
        verbose_name = "Metrik Kaynağı"
        verbose_name_plural = "Metrik Kaynakları"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"

class TechnologyDashboard(BaseModel):
    """Teknoloji bazlı dashboard tanımları"""
    TECHNOLOGY_CHOICES = [
        ('httpd', 'Apache HTTPD'),
        ('nginx', 'Nginx'),
        ('jboss', 'JBoss'),
        ('websphere', 'WebSphere'),
        ('ctg', 'CTG'),
        ('hazelcast', 'Hazelcast'),
        ('provenir', 'Provenir'),
        ('glomo', 'GLOMO'),
        ('octo', 'OCTO'),
        ('tomcat', 'Tomcat'),
        ('iis', 'IIS'),
        ('oracle', 'Oracle'),
        ('postgresql', 'PostgreSQL'),
        ('redis', 'Redis'),
        ('mongodb', 'MongoDB'),
    ]
    
    technology = models.CharField(max_length=50, choices=TECHNOLOGY_CHOICES, unique=True, verbose_name="Teknoloji")
    display_name = models.CharField(max_length=100, verbose_name="Görünen Ad")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    icon_class = models.CharField(max_length=100, default='ri-server-line', verbose_name="İkon CSS Sınıfı")
    color_scheme = models.CharField(max_length=20, default='primary', verbose_name="Renk Şeması")
    metric_sources = models.ManyToManyField(MetricSource, verbose_name="Metrik Kaynakları")
    dashboard_config = models.JSONField(default=dict, verbose_name="Dashboard Konfigürasyonu")
    is_featured = models.BooleanField(default=False, verbose_name="Öne Çıkan")
    
    class Meta:
        verbose_name = "Teknoloji Dashboard"
        verbose_name_plural = "Teknoloji Dashboard'ları"
        ordering = ['display_name']

    def __str__(self):
        return self.display_name

class MetricDefinition(BaseModel):
    """Metrik tanımları"""
    METRIC_TYPES = [
        ('gauge', 'Gauge (Anlık Değer)'),
        ('counter', 'Counter (Sayaç)'),
        ('histogram', 'Histogram'),
        ('summary', 'Summary'),
        ('rate', 'Rate (Oran)'),
        ('percentage', 'Percentage (Yüzde)'),
    ]
    
    CHART_TYPES = [
        ('line', 'Çizgi Grafik'),
        ('area', 'Alan Grafik'),
        ('bar', 'Bar Grafik'),
        ('gauge', 'Gauge'),
        ('stat', 'İstatistik'),
        ('pie', 'Pasta Grafik'),
        ('donut', 'Donut Grafik'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Metrik Adı")
    display_name = models.CharField(max_length=150, verbose_name="Görünen Ad")
    description = models.TextField(verbose_name="Açıklama")
    query = models.TextField(verbose_name="Sorgu (PromQL, SQL, vb.)")
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES, verbose_name="Metrik Tipi")
    chart_type = models.CharField(max_length=20, choices=CHART_TYPES, default='line', verbose_name="Grafik Tipi")
    unit = models.CharField(max_length=20, blank=True, verbose_name="Birim")
    source = models.ForeignKey(MetricSource, on_delete=models.CASCADE, verbose_name="Kaynak")
    technology = models.ForeignKey(TechnologyDashboard, on_delete=models.CASCADE, verbose_name="Teknoloji")
    category = models.CharField(max_length=50, verbose_name="Kategori")
    refresh_interval = models.PositiveIntegerField(default=300, verbose_name="Yenileme Aralığı (saniye)")
    threshold_warning = models.FloatField(null=True, blank=True, verbose_name="Uyarı Eşiği")
    threshold_critical = models.FloatField(null=True, blank=True, verbose_name="Kritik Eşik")
    is_primary = models.BooleanField(default=False, verbose_name="Ana Metrik")
    display_order = models.PositiveIntegerField(default=0, verbose_name="Görüntüleme Sırası")
    
    class Meta:
        verbose_name = "Metrik Tanımı"
        verbose_name_plural = "Metrik Tanımları"
        ordering = ['technology', 'display_order', 'name']

    def __str__(self):
        return f"{self.display_name} ({self.technology.display_name})"

class MetricData(BaseModel):
    """Metrik verileri (cache için)"""
    metric = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE, verbose_name="Metrik")
    timestamp = models.DateTimeField(verbose_name="Zaman Damgası")
    value = models.FloatField(verbose_name="Değer")
    labels = models.JSONField(default=dict, verbose_name="Etiketler")
    
    class Meta:
        verbose_name = "Metrik Verisi"
        verbose_name_plural = "Metrik Verileri"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['metric', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.metric.name} - {self.timestamp}"

class Alert(BaseModel):
    """Performans uyarıları"""
    SEVERITY_CHOICES = [
        ('info', 'Bilgi'),
        ('warning', 'Uyarı'),
        ('critical', 'Kritik'),
        ('emergency', 'Acil'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Aktif'),
        ('resolved', 'Çözüldü'),
        ('acknowledged', 'Onaylandı'),
        ('suppressed', 'Bastırıldı'),
    ]
    
    metric = models.ForeignKey(MetricDefinition, on_delete=models.CASCADE, verbose_name="Metrik")
    title = models.CharField(max_length=200, verbose_name="Uyarı Başlığı")
    description = models.TextField(verbose_name="Açıklama")
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, verbose_name="Önem Derecesi")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Durum")
    threshold_value = models.FloatField(verbose_name="Eşik Değeri")
    current_value = models.FloatField(verbose_name="Mevcut Değer")
    triggered_at = models.DateTimeField(auto_now_add=True, verbose_name="Tetiklenme Zamanı")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Çözülme Zamanı")
    acknowledged_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Onaylayan"
    )
    
    class Meta:
        verbose_name = "Uyarı"
        verbose_name_plural = "Uyarılar"
        ordering = ['-triggered_at']

    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"

    @property
    def severity_color(self):
        """Önem derecesi rengini döndür"""
        colors = {
            'info': 'info',
            'warning': 'warning',
            'critical': 'danger',
            'emergency': 'dark',
        }
        return colors.get(self.severity, 'secondary')

class ObservabilityLog(BaseModel):
    """Observability platform log kayıtları"""
    LOG_LEVELS = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    SOURCE_PLATFORMS = [
        ('splunk', 'Splunk'),
        ('kibana', 'Kibana'),
        ('instana', 'Instana'),
        ('dynatrace', 'Dynatrace'),
    ]
    
    timestamp = models.DateTimeField(verbose_name="Zaman Damgası")
    log_level = models.CharField(max_length=10, choices=LOG_LEVELS, verbose_name="Log Seviyesi")
    message = models.TextField(verbose_name="Log Mesajı")
    application_name = models.CharField(max_length=100, verbose_name="Uygulama Adı")
    host_name = models.CharField(max_length=100, blank=True, verbose_name="Host Adı")
    source_platform = models.CharField(max_length=20, choices=SOURCE_PLATFORMS, verbose_name="Kaynak Platform")
    deep_link_url = models.URLField(verbose_name="Deep Link URL")
    metadata = models.JSONField(default=dict, verbose_name="Metadata")
    
    class Meta:
        verbose_name = "Observability Log"
        verbose_name_plural = "Observability Logları"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['application_name']),
            models.Index(fields=['log_level']),
            models.Index(fields=['source_platform']),
        ]

    def __str__(self):
        return f"{self.application_name} - {self.log_level} - {self.timestamp}"

    @property
    def level_color(self):
        """Log seviyesi rengini döndür"""
        colors = {
            'DEBUG': 'secondary',
            'INFO': 'info',
            'WARNING': 'warning',
            'ERROR': 'danger',
            'CRITICAL': 'dark',
        }
        return colors.get(self.log_level, 'secondary')
