import requests
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import MetricSource, MetricDefinition, MetricData, Alert
import logging

logger = logging.getLogger(__name__)

class MetricCollector:
    """Metrik toplama servisi"""
    
    def __init__(self, source):
        self.source = source
        self.session = requests.Session()
        self._setup_authentication()
    
    def _setup_authentication(self):
        """Kimlik doğrulama ayarları"""
        if self.source.api_key:
            self.session.headers.update({'Authorization': f'Bearer {self.source.api_key}'})
        elif self.source.username and self.source.password:
            self.session.auth = (self.source.username, self.source.password)
        
        if self.source.headers:
            self.session.headers.update(self.source.headers)
    
    def collect_metric(self, metric_definition):
        """Tek bir metrik topla"""
        try:
            if self.source.source_type == 'prometheus':
                return self._collect_prometheus_metric(metric_definition)
            elif self.source.source_type == 'grafana':
                return self._collect_grafana_metric(metric_definition)
            elif self.source.source_type == 'custom_api':
                return self._collect_custom_api_metric(metric_definition)
            else:
                logger.warning(f"Desteklenmeyen kaynak tipi: {self.source.source_type}")
                return None
                
        except Exception as e:
            logger.error(f"Metrik toplama hatası ({metric_definition.name}): {str(e)}")
            return None
    
    def _collect_prometheus_metric(self, metric_definition):
        """Prometheus'tan metrik topla"""
        url = f"{self.source.base_url}/api/v1/query"
        params = {
            'query': metric_definition.query,
            'time': timezone.now().timestamp()
        }
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if data['status'] == 'success' and data['data']['result']:
            result = data['data']['result'][0]
            value = float(result['value'][1])
            labels = result.get('metric', {})
            
            return {
                'value': value,
                'labels': labels,
                'timestamp': timezone.now()
            }
        
        return None
    
    def _collect_grafana_metric(self, metric_definition):
        """Grafana'dan metrik topla"""
        # Grafana API implementasyonu
        # Bu örnekte basit bir implementasyon
        url = f"{self.source.base_url}/api/datasources/proxy/1/api/v1/query"
        params = {'query': metric_definition.query}
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # Grafana response parsing logic burada olacak
        return None
    
    def _collect_custom_api_metric(self, metric_definition):
        """Özel API'dan metrik topla"""
        url = f"{self.source.base_url}/{metric_definition.query}"
        
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Özel API response parsing logic
        if 'value' in data:
            return {
                'value': float(data['value']),
                'labels': data.get('labels', {}),
                'timestamp': timezone.now()
            }
        
        return None

class AlertManager:
    """Uyarı yönetim servisi"""
    
    @staticmethod
    def check_thresholds(metric_definition, current_value):
        """Eşik değerlerini kontrol et ve uyarı oluştur"""
        alerts_created = []
        
        # Kritik eşik kontrolü
        if (metric_definition.threshold_critical is not None and 
            current_value >= metric_definition.threshold_critical):
            
            alert = Alert.objects.create(
                metric=metric_definition,
                title=f"{metric_definition.name} - Kritik Eşik Aşıldı",
                description=f"Mevcut değer ({current_value}) kritik eşiği ({metric_definition.threshold_critical}) aştı.",
                severity='critical',
                threshold_value=metric_definition.threshold_critical,
                current_value=current_value
            )
            alerts_created.append(alert)
        
        # Uyarı eşiği kontrolü
        elif (metric_definition.threshold_warning is not None and 
              current_value >= metric_definition.threshold_warning):
            
            alert = Alert.objects.create(
                metric=metric_definition,
                title=f"{metric_definition.name} - Uyarı Eşiği Aşıldı",
                description=f"Mevcut değer ({current_value}) uyarı eşiğini ({metric_definition.threshold_warning}) aştı.",
                severity='warning',
                threshold_value=metric_definition.threshold_warning,
                current_value=current_value
            )
            alerts_created.append(alert)
        
        return alerts_created
    
    @staticmethod
    def resolve_alerts(metric_definition, current_value):
        """Eşik altına düşen uyarıları çöz"""
        active_alerts = Alert.objects.filter(
            metric=metric_definition,
            status='active'
        )
        
        resolved_count = 0
        for alert in active_alerts:
            if current_value < alert.threshold_value:
                alert.status = 'resolved'
                alert.resolved_at = timezone.now()
                alert.save()
                resolved_count += 1
        
        return resolved_count

class PerformanceService:
    """Ana performans servisi"""
    
    @staticmethod
    def collect_all_metrics():
        """Tüm metrikleri topla"""
        collected_count = 0
        error_count = 0
        
        for source in MetricSource.objects.filter(is_active=True):
            collector = MetricCollector(source)
            
            for metric in MetricDefinition.objects.filter(source=source, is_active=True):
                try:
                    data = collector.collect_metric(metric)
                    
                    if data:
                        # Metrik verisini kaydet
                        MetricData.objects.create(
                            metric=metric,
                            timestamp=data['timestamp'],
                            value=data['value'],
                            labels=data['labels']
                        )
                        
                        # Eski verileri temizle (30 gün)
                        cutoff_date = timezone.now() - timedelta(days=30)
                        MetricData.objects.filter(
                            metric=metric,
                            timestamp__lt=cutoff_date
                        ).delete()
                        
                        # Uyarı kontrolü
                        AlertManager.check_thresholds(metric, data['value'])
                        AlertManager.resolve_alerts(metric, data['value'])
                        
                        collected_count += 1
                        logger.info(f"Metrik toplandı: {metric.name} = {data['value']}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Metrik toplama hatası ({metric.name}): {str(e)}")
        
        return {
            'collected': collected_count,
            'errors': error_count
        }
    
    @staticmethod
    def get_metric_data(metric_id, time_range='1h'):
        """Metrik verilerini getir"""
        try:
            metric = MetricDefinition.objects.get(id=metric_id)
            
            # Zaman aralığını hesapla
            time_ranges = {
                '1h': timedelta(hours=1),
                '6h': timedelta(hours=6),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }
            
            start_time = timezone.now() - time_ranges.get(time_range, timedelta(hours=1))
            
            data = MetricData.objects.filter(
                metric=metric,
                timestamp__gte=start_time
            ).order_by('timestamp')
            
            return {
                'metric': metric,
                'data': [
                    {
                        'timestamp': item.timestamp.isoformat(),
                        'value': item.value,
                        'labels': item.labels
                    }
                    for item in data
                ]
            }
            
        except MetricDefinition.DoesNotExist:
            return None
