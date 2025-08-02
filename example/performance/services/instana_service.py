import requests
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from typing import Dict, List, Optional
import logging
import urllib.parse

logger = logging.getLogger(__name__)

class InstanaService:
    """Instana API entegrasyon servisi"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'INSTANA_URL', '')
        self.api_token = getattr(settings, 'INSTANA_API_TOKEN', '')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'apiToken {self.api_token}',
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, endpoint: str, params: Dict = None, data: Dict = None) -> Optional[Dict]:
        """API isteği yap"""
        try:
            url = f"{self.base_url}/api/{endpoint}"
            
            if data:
                response = self.session.post(url, json=data, params=params, timeout=30)
            else:
                response = self.session.get(url, params=params, timeout=30)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Instana API hatası: {str(e)}")
            return None
    
    def _get_time_range_params(self, time_range: str) -> Dict:
        """Zaman aralığı parametrelerini döndür"""
        now = timezone.now()
        time_ranges = {
            '1h': now - timedelta(hours=1),
            '6h': now - timedelta(hours=6),
            '24h': now - timedelta(hours=24),
            '7d': now - timedelta(days=7),
            '30d': now - timedelta(days=30),
        }
        
        start_time = time_ranges.get(time_range, now - timedelta(hours=24))
        
        return {
            'from': int(start_time.timestamp() * 1000),
            'to': int(now.timestamp() * 1000)
        }
    
    def get_error_logs(self, application_name: str = None, time_range: str = '24h') -> List[Dict]:
        """Hata loglarını getir"""
        cache_key = f"instana_errors_{application_name or 'all'}_{time_range}"
        
        def fetch_error_logs():
            time_params = self._get_time_range_params(time_range)
            
            # Instana log search query
            query_data = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "range": {
                                    "timestamp": {
                                        "gte": time_params['from'],
                                        "lte": time_params['to']
                                    }
                                }
                            },
                            {
                                "bool": {
                                    "should": [
                                        {"match": {"severity": "ERROR"}},
                                        {"match": {"severity": "FATAL"}},
                                        {"match": {"severity": "CRITICAL"}},
                                        {"match": {"level": "ERROR"}},
                                        {"wildcard": {"message": "*error*"}},
                                        {"wildcard": {"message": "*exception*"}},
                                        {"wildcard": {"message": "*failed*"}},
                                    ],
                                    "minimum_should_match": 1
                                }
                            }
                        ]
                    }
                },
                "size": 1000,
                "sort": [{"timestamp": {"order": "desc"}}]
            }
            
            # Uygulama filtresi
            if application_name:
                query_data["query"]["bool"]["must"].append({
                    "bool": {
                        "should": [
                            {"wildcard": {"service": f"*{application_name}*"}},
                            {"wildcard": {"application": f"*{application_name}*"}},
                            {"wildcard": {"host": f"*{application_name}*"}},
                        ],
                        "minimum_should_match": 1
                    }
                })
            
            # Instana logs API'sine sorgu gönder
            data = self._make_request('logs/search', data=query_data)
            
            if not data or 'hits' not in data:
                return []
            
            logs = []
            for hit in data['hits']:
                source = hit.get('_source', {})
                
                # Deep link URL oluştur
                log_id = hit.get('_id', '')
                timestamp = source.get('timestamp', time_params['from'])
                deep_link = f"{self.base_url}/#/logs?logId={log_id}&timestamp={timestamp}"
                
                # Uygulama adını çıkar
                app_name = (
                    source.get('application') or 
                    source.get('service') or 
                    source.get('host') or
                    application_name or
                    'Unknown'
                )
                
                # Log seviyesini belirle
                log_level = (
                    source.get('severity') or 
                    source.get('level') or 
                    'ERROR'
                ).upper()
                
                if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                    log_level = 'ERROR'
                
                logs.append({
                    'timestamp': datetime.fromtimestamp(source.get('timestamp', 0) / 1000).isoformat(),
                    'log_level': log_level,
                    'message': source.get('message', '')[:500],  # İlk 500 karakter
                    'application_name': app_name,
                    'host_name': source.get('host', ''),
                    'source_platform': 'instana',
                    'deep_link_url': deep_link,
                    'metadata': {
                        'trace_id': source.get('traceId'),
                        'span_id': source.get('spanId'),
                        'service': source.get('service'),
                        'operation': source.get('operation'),
                    }
                })
            
            return logs
        
        return cache.get_or_set(cache_key, fetch_error_logs, 300)
    
    def get_application_metrics(self, application_name: str, time_range: str = '24h') -> Dict:
        """Uygulama metriklerini getir"""
        cache_key = f"instana_metrics_{application_name}_{time_range}"
        
        def fetch_metrics():
            time_params = self._get_time_range_params(time_range)
            
            # Service metrics query
            metrics_query = {
                "metrics": [
                    {"metric": "calls", "aggregation": "SUM"},
                    {"metric": "errors", "aggregation": "SUM"},
                    {"metric": "latency", "aggregation": "MEAN"},
                ],
                "group": {
                    "groupbyTag": "service.name"
                },
                "timeFrame": {
                    "from": time_params['from'],
                    "to": time_params['to']
                },
                "filter": {
                    "entity": "service",
                    "query": f"service.name:*{application_name}*"
                }
            }
            
            data = self._make_request('metrics', data=metrics_query)
            
            metrics = {'request_count': 0, 'error_count': 0, 'avg_response_time': 0}
            
            if data and 'items' in data:
                for item in data['items']:
                    if item.get('service.name') and application_name.lower() in item['service.name'].lower():
                        metrics['request_count'] += item.get('calls', 0)
                        metrics['error_count'] += item.get('errors', 0)
                        if item.get('latency'):
                            metrics['avg_response_time'] = item['latency']
            
            return metrics
        
        return cache.get_or_set(cache_key, fetch_metrics, 300)
    
    def get_dashboard_summary(self, time_range: str = '24h') -> Dict:
        """Dashboard özet bilgilerini getir"""
        cache_key = f"instana_dashboard_summary_{time_range}"
        
        def fetch_summary():
            time_params = self._get_time_range_params(time_range)
            
            # Global metrics query
            summary_query = {
                "metrics": [
                    {"metric": "calls", "aggregation": "SUM"},
                    {"metric": "errors", "aggregation": "SUM"},
                    {"metric": "latency", "aggregation": "MEAN"},
                ],
                "timeFrame": {
                    "from": time_params['from'],
                    "to": time_params['to']
                }
            }
            
            data = self._make_request('metrics', data=summary_query)
            
            summary = {
                'total_requests': 0,
                'total_errors': 0,
                'avg_response_time': 0,
                'applications': [],
                'error_rate': 0
            }
            
            if data and 'items' in data:
                total_calls = sum(item.get('calls', 0) for item in data['items'])
                total_errors = sum(item.get('errors', 0) for item in data['items'])
                
                summary['total_requests'] = total_calls
                summary['total_errors'] = total_errors
                summary['error_rate'] = (total_errors / total_calls * 100) if total_calls > 0 else 0
                
                # Ortalama response time
                latencies = [item.get('latency', 0) for item in data['items'] if item.get('latency')]
                if latencies:
                    summary['avg_response_time'] = sum(latencies) / len(latencies)
            
            # Top applications by error count
            apps_query = {
                "metrics": [
                    {"metric": "errors", "aggregation": "SUM"},
                    {"metric": "calls", "aggregation": "SUM"},
                ],
                "group": {
                    "groupbyTag": "service.name"
                },
                "timeFrame": {
                    "from": time_params['from'],
                    "to": time_params['to']
                }
            }
            
            apps_data = self._make_request('metrics', data=apps_query)
            if apps_data and 'items' in apps_data:
                apps = []
                for item in apps_data['items']:
                    if item.get('service.name'):
                        apps.append({
                            'name': item['service.name'],
                            'error_count': item.get('errors', 0),
                            'request_count': item.get('calls', 0)
                        })
                
                # En çok hata verenleri sırala
                summary['applications'] = sorted(apps, key=lambda x: x['error_count'], reverse=True)[:10]
            
            return summary
        
        return cache.get_or_set(cache_key, fetch_summary, 300)
    
    def get_trace_analytics(self, application_name: str = None, time_range: str = '24h') -> Dict:
        """Trace analitik verilerini getir"""
        cache_key = f"instana_traces_{application_name or 'all'}_{time_range}"
        
        def fetch_traces():
            time_params = self._get_time_range_params(time_range)
            
            # Trace search query
            trace_query = {
                "timeFrame": {
                    "from": time_params['from'],
                    "to": time_params['to']
                },
                "filter": {
                    "entity": "trace"
                },
                "size": 100
            }
            
            if application_name:
                trace_query["filter"]["query"] = f"service.name:*{application_name}*"
            
            data = self._make_request('traces/search', data=trace_query)
            
            analytics = {
                'total_traces': 0,
                'error_traces': 0,
                'slow_traces': 0,
                'avg_duration': 0,
                'trace_distribution': []
            }
            
            if data and 'items' in data:
                traces = data['items']
                analytics['total_traces'] = len(traces)
                
                durations = []
                error_count = 0
                slow_count = 0
                
                for trace in traces:
                    duration = trace.get('duration', 0)
                    durations.append(duration)
                    
                    if trace.get('erroneous', False):
                        error_count += 1
                    
                    # 1 saniyeden uzun trace'leri yavaş kabul et
                    if duration > 1000:
                        slow_count += 1
                
                analytics['error_traces'] = error_count
                analytics['slow_traces'] = slow_count
                analytics['avg_duration'] = sum(durations) / len(durations) if durations else 0
                
                # Duration distribution
                if durations:
                    durations.sort()
                    analytics['trace_distribution'] = {
                        'p50': durations[len(durations) // 2],
                        'p95': durations[int(len(durations) * 0.95)],
                        'p99': durations[int(len(durations) * 0.99)],
                        'max': max(durations),
                        'min': min(durations)
                    }
            
            return analytics
        
        return cache.get_or_set(cache_key, fetch_traces, 300)
