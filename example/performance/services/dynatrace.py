import requests
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class DynatraceService:
    """Dynatrace API entegrasyon servisi"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'DYNATRACE_URL', '')
        self.api_token = getattr(settings, 'DYNATRACE_API_TOKEN', '')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Api-Token {self.api_token}',
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """API isteği yap"""
        try:
            url = f"{self.base_url}/api/v2/{endpoint}"
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Dynatrace API hatası: {str(e)}")
            return None
    
    def _get_cached_data(self, cache_key: str, fetch_func, cache_timeout: int = 300):
        """Cache'den veri al veya API'den çek"""
        data = cache.get(cache_key)
        if data is None:
            data = fetch_func()
            if data:
                cache.set(cache_key, data, cache_timeout)
        return data
    
    def get_technology_metrics(self, technology: str, time_range: str = '1h') -> Dict:
        """Teknoloji bazlı metrikleri getir"""
        cache_key = f"dynatrace_metrics_{technology}_{time_range}"
        
        def fetch_metrics():
            # Zaman aralığını hesapla
            end_time = timezone.now()
            time_ranges = {
                '1h': timedelta(hours=1),
                '6h': timedelta(hours=6),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
                '30d': timedelta(days=30),
            }
            start_time = end_time - time_ranges.get(time_range, timedelta(hours=1))
            
            # Teknoloji bazlı metrik sorgularını tanımla
            metric_queries = self._get_technology_queries(technology)
            
            results = {}
            for metric_name, query in metric_queries.items():
                params = {
                    'metricSelector': query,
                    'from': start_time.isoformat(),
                    'to': end_time.isoformat(),
                    'resolution': self._get_resolution(time_range)
                }
                
                data = self._make_request('metrics/query', params)
                if data and 'result' in data:
                    results[metric_name] = self._process_metric_data(data['result'])
            
            return results
        
        return self._get_cached_data(cache_key, fetch_metrics, 120)
    
    def _get_technology_queries(self, technology: str) -> Dict[str, str]:
        """Teknoloji bazlı metrik sorgularını döndür"""
        queries = {
            'httpd': {
                'cpu_usage': 'builtin:host.cpu.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:apache)")))',
                'memory_usage': 'builtin:host.mem.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:apache)")))',
                'request_rate': 'builtin:service.requestCount.rate:filter(eq("dt.entity.service",entitySelector("type(SERVICE),tag(technology:apache)")))',
                'response_time': 'builtin:service.response.time:filter(eq("dt.entity.service",entitySelector("type(SERVICE),tag(technology:apache)")))',
                'error_rate': 'builtin:service.errors.rate:filter(eq("dt.entity.service",entitySelector("type(SERVICE),tag(technology:apache)")))',
            },
            'nginx': {
                'cpu_usage': 'builtin:host.cpu.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:nginx)")))',
                'memory_usage': 'builtin:host.mem.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:nginx)")))',
                'request_rate': 'builtin:service.requestCount.rate:filter(eq("dt.entity.service",entitySelector("type(SERVICE),tag(technology:nginx)")))',
                'response_time': 'builtin:service.response.time:filter(eq("dt.entity.service",entitySelector("type(SERVICE),tag(technology:nginx)")))',
                'active_connections': 'builtin:tech.nginx.connections.active:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:nginx)")))',
            },
            'jboss': {
                'cpu_usage': 'builtin:host.cpu.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:jboss)")))',
                'memory_usage': 'builtin:host.mem.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:jboss)")))',
                'heap_usage': 'builtin:tech.jvm.memory.heap.used:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:jboss)")))',
                'gc_time': 'builtin:tech.jvm.memory.gc.collectionTime:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:jboss)")))',
                'thread_count': 'builtin:tech.jvm.threading.threadCount:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:jboss)")))',
                'request_rate': 'builtin:service.requestCount.rate:filter(eq("dt.entity.service",entitySelector("type(SERVICE),tag(technology:jboss)")))',
                'response_time': 'builtin:service.response.time:filter(eq("dt.entity.service",entitySelector("type(SERVICE),tag(technology:jboss)")))',
            },
            'websphere': {
                'cpu_usage': 'builtin:host.cpu.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:websphere)")))',
                'memory_usage': 'builtin:host.mem.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:websphere)")))',
                'heap_usage': 'builtin:tech.jvm.memory.heap.used:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:websphere)")))',
                'thread_pool_usage': 'builtin:tech.websphere.threadPool.activeThreads:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:websphere)")))',
                'connection_pool_usage': 'builtin:tech.websphere.connectionPool.usedConnections:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:websphere)")))',
                'request_rate': 'builtin:service.requestCount.rate:filter(eq("dt.entity.service",entitySelector("type(SERVICE),tag(technology:websphere)")))',
            },
            'hazelcast': {
                'cpu_usage': 'builtin:host.cpu.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:hazelcast)")))',
                'memory_usage': 'builtin:host.mem.usage:filter(eq("dt.entity.host",entitySelector("type(HOST),tag(technology:hazelcast)")))',
                'cluster_size': 'builtin:tech.hazelcast.cluster.memberCount:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:hazelcast)")))',
                'map_size': 'builtin:tech.hazelcast.map.size:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:hazelcast)")))',
                'operations_rate': 'builtin:tech.hazelcast.operations.rate:filter(eq("dt.entity.process_group",entitySelector("type(PROCESS_GROUP),tag(technology:hazelcast)")))',
            }
        }
        
        return queries.get(technology, {})
    
    def _get_resolution(self, time_range: str) -> str:
        """Zaman aralığına göre çözünürlük döndür"""
        resolutions = {
            '1h': '1m',
            '6h': '5m',
            '24h': '1h',
            '7d': '1h',
            '30d': '1d',
        }
        return resolutions.get(time_range, '5m')
    
    def _process_metric_data(self, result_data: List) -> Dict:
        """Metrik verisini işle"""
        if not result_data:
            return {'values': [], 'timestamps': [], 'current': 0, 'average': 0}
        
        # İlk sonucu al (genellikle tek sonuç olur)
        metric_result = result_data[0]
        data_points = metric_result.get('data', [])
        
        if not data_points:
            return {'values': [], 'timestamps': [], 'current': 0, 'average': 0}
        
        values = []
        timestamps = []
        
        for point in data_points:
            if point.get('values') and len(point['values']) > 0:
                values.append(point['values'][0])
                timestamps.append(point['timestamp'])
        
        current_value = values[-1] if values else 0
        average_value = sum(values) / len(values) if values else 0
        
        return {
            'values': values,
            'timestamps': timestamps,
            'current': round(current_value, 2),
            'average': round(average_value, 2),
            'min': round(min(values), 2) if values else 0,
            'max': round(max(values), 2) if values else 0,
        }
    
    def get_host_metrics(self, host_id: str, time_range: str = '1h') -> Dict:
        """Host bazlı metrikleri getir"""
        cache_key = f"dynatrace_host_{host_id}_{time_range}"
        
        def fetch_host_metrics():
            end_time = timezone.now()
            time_ranges = {
                '1h': timedelta(hours=1),
                '6h': timedelta(hours=6),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
            }
            start_time = end_time - time_ranges.get(time_range, timedelta(hours=1))
            
            metrics = {
                'cpu': f'builtin:host.cpu.usage:filter(eq("dt.entity.host","{host_id}"))',
                'memory': f'builtin:host.mem.usage:filter(eq("dt.entity.host","{host_id}"))',
                'disk': f'builtin:host.disk.usage:filter(eq("dt.entity.host","{host_id}"))',
                'network_in': f'builtin:host.net.bytesRx:filter(eq("dt.entity.host","{host_id}"))',
                'network_out': f'builtin:host.net.bytesTx:filter(eq("dt.entity.host","{host_id}"))',
            }
            
            results = {}
            for metric_name, query in metrics.items():
                params = {
                    'metricSelector': query,
                    'from': start_time.isoformat(),
                    'to': end_time.isoformat(),
                    'resolution': self._get_resolution(time_range)
                }
                
                data = self._make_request('metrics/query', params)
                if data and 'result' in data:
                    results[metric_name] = self._process_metric_data(data['result'])
            
            return results
        
        return self._get_cached_data(cache_key, fetch_host_metrics, 120)
    
    def get_service_metrics(self, service_id: str, time_range: str = '1h') -> Dict:
        """Servis bazlı metrikleri getir"""
        cache_key = f"dynatrace_service_{service_id}_{time_range}"
        
        def fetch_service_metrics():
            end_time = timezone.now()
            time_ranges = {
                '1h': timedelta(hours=1),
                '6h': timedelta(hours=6),
                '24h': timedelta(hours=24),
                '7d': timedelta(days=7),
            }
            start_time = end_time - time_ranges.get(time_range, timedelta(hours=1))
            
            metrics = {
                'request_count': f'builtin:service.requestCount.rate:filter(eq("dt.entity.service","{service_id}"))',
                'response_time': f'builtin:service.response.time:filter(eq("dt.entity.service","{service_id}"))',
                'error_rate': f'builtin:service.errors.rate:filter(eq("dt.entity.service","{service_id}"))',
                'throughput': f'builtin:service.throughput:filter(eq("dt.entity.service","{service_id}"))',
            }
            
            results = {}
            for metric_name, query in metrics.items():
                params = {
                    'metricSelector': query,
                    'from': start_time.isoformat(),
                    'to': end_time.isoformat(),
                    'resolution': self._get_resolution(time_range)
                }
                
                data = self._make_request('metrics/query', params)
                if data and 'result' in data:
                    results[metric_name] = self._process_metric_data(data['result'])
            
            return results
        
        return self._get_cached_data(cache_key, fetch_service_metrics, 120)
    
    def get_problems(self, technology: str = None) -> List[Dict]:
        """Problemleri getir"""
        cache_key = f"dynatrace_problems_{technology or 'all'}"
        
        def fetch_problems():
            params = {
                'problemSelector': 'status("OPEN")',
                'fields': 'displayId,title,impactLevel,status,startTime,entityTags'
            }
            
            if technology:
                params['entitySelector'] = f'type("SERVICE"),tag("technology:{technology}")'
            
            data = self._make_request('problems', params)
            if data and 'problems' in data:
                return data['problems']
            return []
        
        return self._get_cached_data(cache_key, fetch_problems, 300)
    
    def get_entities(self, entity_type: str, technology: str = None) -> List[Dict]:
        """Entity'leri getir"""
        cache_key = f"dynatrace_entities_{entity_type}_{technology or 'all'}"
        
        def fetch_entities():
            params = {
                'entitySelector': f'type("{entity_type.upper()}")',
                'fields': 'displayName,entityId,tags,properties'
            }
            
            if technology:
                params['entitySelector'] += f',tag("technology:{technology}")'
            
            data = self._make_request('entities', params)
            if data and 'entities' in data:
                return data['entities']
            return []
        
        return self._get_cached_data(cache_key, fetch_entities, 600)
