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

class KibanaService:
    """Kibana/Elasticsearch API entegrasyon servisi"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'KIBANA_URL', '')
        self.elasticsearch_url = getattr(settings, 'ELASTICSEARCH_URL', '')
        self.username = getattr(settings, 'KIBANA_USERNAME', '')
        self.password = getattr(settings, 'KIBANA_PASSWORD', '')
        self.api_key = getattr(settings, 'KIBANA_API_KEY', '')
        
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'ApiKey {self.api_key}',
                'Content-Type': 'application/json'
            })
        elif self.username and self.password:
            self.session.auth = (self.username, self.password)
            self.session.headers.update({'Content-Type': 'application/json'})
    
    def _make_elasticsearch_request(self, endpoint: str, query: Dict) -> Optional[Dict]:
        """Elasticsearch API isteği yap"""
        try:
            url = f"{self.elasticsearch_url}/{endpoint}"
            response = self.session.post(url, json=query, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Elasticsearch API hatası: {str(e)}")
            return None
    
    def _build_time_range_query(self, time_range: str) -> Dict:
        """Zaman aralığı sorgusu oluştur"""
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
            "range": {
                "@timestamp": {
                    "gte": start_time.isoformat(),
                    "lte": now.isoformat()
                }
            }
        }
    
    def get_error_logs(self, application_name: str = None, time_range: str = '24h') -> List[Dict]:
        """Hata loglarını getir"""
        cache_key = f"kibana_errors_{application_name or 'all'}_{time_range}"
        
        def fetch_error_logs():
            # Elasticsearch sorgusu oluştur
            query = {
                "size": 1000,
                "sort": [{"@timestamp": {"order": "desc"}}],
                "query": {
                    "bool": {
                        "must": [
                            self._build_time_range_query(time_range),
                            {
                                "bool": {
                                    "should": [
                                        {"match": {"level": "ERROR"}},
                                        {"match": {"level": "FATAL"}},
                                        {"match": {"level": "CRITICAL"}},
                                        {"range": {"status": {"gte": 400}}},
                                        {"wildcard": {"message": "*error*"}},
                                        {"wildcard": {"message": "*exception*"}},
                                    ],
                                    "minimum_should_match": 1
                                }
                            }
                        ]
                    }
                }
            }
            
            # Uygulama filtresi ekle
            if application_name:
                query["query"]["bool"]["must"].append({
                    "bool": {
                        "should": [
                            {"wildcard": {"application": f"*{application_name}*"}},
                            {"wildcard": {"service": f"*{application_name}*"}},
                            {"wildcard": {"host": f"*{application_name}*"}},
                            {"wildcard": {"kubernetes.pod.name": f"*{application_name}*"}},
                        ],
                        "minimum_should_match": 1
                    }
                })
            
            # Elasticsearch'e sorgu gönder
            data = self._make_elasticsearch_request('_search', query)
            
            if not data or 'hits' not in data:
                return []
            
            logs = []
            for hit in data['hits']['hits']:
                source = hit['_source']
                
                # Deep link URL oluştur
                index_name = hit['_index']
                doc_id = hit['_id']
                deep_link = f"{self.base_url}/app/discover#/doc/{index_name}?id={doc_id}"
                
                # Uygulama adını çıkar
                app_name = (
                    source.get('application') or 
                    source.get('service') or 
                    source.get('kubernetes', {}).get('pod', {}).get('name') or
                    source.get('host') or
                    application_name or
                    'Unknown'
                )
                
                # Log seviyesini belirle
                log_level = source.get('level', 'ERROR').upper()
                if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                    # HTTP status code'a göre seviye belirle
                    status = source.get('status', 0)
                    if status >= 500:
                        log_level = 'CRITICAL'
                    elif status >= 400:
                        log_level = 'ERROR'
                    else:
                        log_level = 'ERROR'
                
                logs.append({
                    'timestamp': source.get('@timestamp', ''),
                    'log_level': log_level,
                    'message': source.get('message', '')[:500],  # İlk 500 karakter
                    'application_name': app_name,
                    'host_name': source.get('host', ''),
                    'source_platform': 'kibana',
                    'deep_link_url': deep_link,
                    'metadata': {
                        'index': index_name,
                        'status': source.get('status'),
                        'method': source.get('method'),
                        'url': source.get('url'),
                        'user_agent': source.get('user_agent'),
                    }
                })
            
            return logs
        
        return cache.get_or_set(cache_key, fetch_error_logs, 300)
    
    def get_application_metrics(self, application_name: str, time_range: str = '24h') -> Dict:
        """Uygulama metriklerini getir"""
        cache_key = f"kibana_metrics_{application_name}_{time_range}"
        
        def fetch_metrics():
            metrics = {}
            
            # Request count aggregation
            request_query = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [
                            self._build_time_range_query(time_range),
                            {
                                "bool": {
                                    "should": [
                                        {"wildcard": {"application": f"*{application_name}*"}},
                                        {"wildcard": {"service": f"*{application_name}*"}},
                                    ],
                                    "minimum_should_match": 1
                                }
                            }
                        ]
                    }
                },
                "aggs": {
                    "request_count": {"value_count": {"field": "@timestamp"}},
                    "error_count": {
                        "filter": {
                            "bool": {
                                "should": [
                                    {"range": {"status": {"gte": 400}}},
                                    {"match": {"level": "ERROR"}},
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    },
                    "avg_response_time": {
                        "avg": {"field": "response_time"}
                    }
                }
            }
            
            data = self._make_elasticsearch_request('_search', request_query)
            
            if data and 'aggregations' in data:
                aggs = data['aggregations']
                metrics['request_count'] = aggs.get('request_count', {}).get('value', 0)
                metrics['error_count'] = aggs.get('error_count', {}).get('doc_count', 0)
                metrics['avg_response_time'] = aggs.get('avg_response_time', {}).get('value', 0) or 0
            else:
                metrics = {'request_count': 0, 'error_count': 0, 'avg_response_time': 0}
            
            return metrics
        
        return cache.get_or_set(cache_key, fetch_metrics, 300)
    
    def get_dashboard_summary(self, time_range: str = '24h') -> Dict:
        """Dashboard özet bilgilerini getir"""
        cache_key = f"kibana_dashboard_summary_{time_range}"
        
        def fetch_summary():
            # Özet sorgusu
            summary_query = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [self._build_time_range_query(time_range)]
                    }
                },
                "aggs": {
                    "total_logs": {"value_count": {"field": "@timestamp"}},
                    "error_logs": {
                        "filter": {
                            "bool": {
                                "should": [
                                    {"match": {"level": "ERROR"}},
                                    {"match": {"level": "FATAL"}},
                                    {"match": {"level": "CRITICAL"}},
                                    {"range": {"status": {"gte": 500}}},
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    },
                    "warning_logs": {
                        "filter": {
                            "bool": {
                                "should": [
                                    {"match": {"level": "WARNING"}},
                                    {"match": {"level": "WARN"}},
                                    {"range": {"status": {"gte": 400, "lt": 500}}},
                                ],
                                "minimum_should_match": 1
                            }
                        }
                    },
                    "top_applications": {
                        "terms": {
                            "field": "application.keyword",
                            "size": 10,
                            "order": {"error_count": "desc"}
                        },
                        "aggs": {
                            "error_count": {
                                "filter": {
                                    "bool": {
                                        "should": [
                                            {"match": {"level": "ERROR"}},
                                            {"range": {"status": {"gte": 400}}},
                                        ],
                                        "minimum_should_match": 1
                                    }
                                }
                            }
                        }
                    },
                    "status_codes": {
                        "terms": {
                            "field": "status",
                            "size": 20
                        }
                    }
                }
            }
            
            data = self._make_elasticsearch_request('_search', summary_query)
            
            if not data or 'aggregations' not in data:
                return {
                    'total_logs': 0,
                    'error_logs': 0,
                    'warning_logs': 0,
                    'applications': [],
                    'status_codes': []
                }
            
            aggs = data['aggregations']
            
            return {
                'total_logs': aggs.get('total_logs', {}).get('value', 0),
                'error_logs': aggs.get('error_logs', {}).get('doc_count', 0),
                'warning_logs': aggs.get('warning_logs', {}).get('doc_count', 0),
                'applications': [
                    {
                        'key': bucket['key'],
                        'doc_count': bucket['doc_count'],
                        'error_count': bucket['error_count']['doc_count']
                    }
                    for bucket in aggs.get('top_applications', {}).get('buckets', [])
                ],
                'status_codes': [
                    {'status': bucket['key'], 'count': bucket['doc_count']}
                    for bucket in aggs.get('status_codes', {}).get('buckets', [])
                ]
            }
        
        return cache.get_or_set(cache_key, fetch_summary, 300)
    
    def get_log_timeline(self, application_name: str = None, time_range: str = '24h') -> Dict:
        """Log zaman çizelgesi getir"""
        cache_key = f"kibana_timeline_{application_name or 'all'}_{time_range}"
        
        def fetch_timeline():
            # Zaman bazlı histogram sorgusu
            query = {
                "size": 0,
                "query": {
                    "bool": {
                        "must": [self._build_time_range_query(time_range)]
                    }
                },
                "aggs": {
                    "timeline": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "fixed_interval": "1h",
                            "extended_bounds": {
                                "min": (timezone.now() - timedelta(hours=24)).isoformat(),
                                "max": timezone.now().isoformat()
                            }
                        },
                        "aggs": {
                            "errors": {
                                "filter": {
                                    "bool": {
                                        "should": [
                                            {"match": {"level": "ERROR"}},
                                            {"range": {"status": {"gte": 400}}},
                                        ],
                                        "minimum_should_match": 1
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            # Uygulama filtresi
            if application_name:
                query["query"]["bool"]["must"].append({
                    "wildcard": {"application": f"*{application_name}*"}
                })
            
            data = self._make_elasticsearch_request('_search', query)
            
            if not data or 'aggregations' not in data:
                return {'timestamps': [], 'total_counts': [], 'error_counts': []}
            
            buckets = data['aggregations']['timeline']['buckets']
            
            timestamps = []
            total_counts = []
            error_counts = []
            
            for bucket in buckets:
                timestamps.append(bucket['key_as_string'])
                total_counts.append(bucket['doc_count'])
                error_counts.append(bucket['errors']['doc_count'])
            
            return {
                'timestamps': timestamps,
                'total_counts': total_counts,
                'error_counts': error_counts
            }
        
        return cache.get_or_set(cache_key, fetch_timeline, 300)
