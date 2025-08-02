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

class SplunkService:
    """Splunk API entegrasyon servisi"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'SPLUNK_URL', '')
        self.username = getattr(settings, 'SPLUNK_USERNAME', '')
        self.password = getattr(settings, 'SPLUNK_PASSWORD', '')
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.verify = False  # SSL doğrulamasını devre dışı bırak (gerekirse)
    
    def _get_session_key(self) -> Optional[str]:
        """Splunk session key al"""
        cache_key = 'splunk_session_key'
        session_key = cache.get(cache_key)
        
        if not session_key:
            try:
                url = f"{self.base_url}/services/auth/login"
                data = {
                    'username': self.username,
                    'password': self.password,
                    'output_mode': 'json'
                }
                
                response = self.session.post(url, data=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                session_key = result['sessionKey']
                
                # Session key'i 30 dakika cache'le
                cache.set(cache_key, session_key, 1800)
                
            except Exception as e:
                logger.error(f"Splunk session key alınamadı: {str(e)}")
                return None
        
        return session_key
    
    def _make_search_request(self, search_query: str, earliest_time: str = '-24h', latest_time: str = 'now') -> Optional[Dict]:
        """Splunk arama isteği yap"""
        session_key = self._get_session_key()
        if not session_key:
            return None
        
        try:
            # Arama işini başlat
            url = f"{self.base_url}/services/search/jobs"
            headers = {
                'Authorization': f'Splunk {session_key}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'search': search_query,
                'earliest_time': earliest_time,
                'latest_time': latest_time,
                'output_mode': 'json'
            }
            
            response = self.session.post(url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            job_response = response.json()
            job_id = job_response['sid']
            
            # Arama tamamlanana kadar bekle
            results_url = f"{self.base_url}/services/search/jobs/{job_id}/results"
            
            import time
            max_wait = 60  # 60 saniye maksimum bekleme
            wait_time = 0
            
            while wait_time < max_wait:
                status_url = f"{self.base_url}/services/search/jobs/{job_id}"
                status_response = self.session.get(status_url, headers=headers, params={'output_mode': 'json'})
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data['entry'][0]['content']['isDone']:
                        break
                
                time.sleep(2)
                wait_time += 2
            
            # Sonuçları al
            results_response = self.session.get(results_url, headers=headers, params={'output_mode': 'json'})
            results_response.raise_for_status()
            
            return results_response.json()
            
        except Exception as e:
            logger.error(f"Splunk arama hatası: {str(e)}")
            return None
    
    def get_error_logs(self, application_name: str = None, time_range: str = '24h') -> List[Dict]:
        """Hata loglarını getir"""
        cache_key = f"splunk_errors_{application_name or 'all'}_{time_range}"
        
        def fetch_error_logs():
            # Splunk arama sorgusu
            base_query = 'search index=* (ERROR OR FATAL OR "HTTP 5*" OR "HTTP 4*")'
            
            if application_name:
                base_query += f' AND (source="*{application_name}*" OR host="*{application_name}*")'
            
            # Sonuçları formatla
            query = f'{base_query} | head 1000 | table _time, source, host, _raw | sort -_time'
            
            earliest_time = f'-{time_range}'
            data = self._make_search_request(query, earliest_time)
            
            if not data or 'results' not in data:
                return []
            
            logs = []
            for result in data['results']:
                # Deep link URL oluştur
                encoded_query = urllib.parse.quote(base_query)
                deep_link = f"{self.base_url}/app/search/search?q={encoded_query}&earliest={earliest_time}&latest=now"
                
                # Uygulama adını çıkar
                app_name = application_name
                if not app_name:
                    source = result.get('source', '')
                    host = result.get('host', '')
                    # Basit uygulama adı çıkarma mantığı
                    if 'tomcat' in source.lower():
                        app_name = 'Tomcat'
                    elif 'jboss' in source.lower():
                        app_name = 'JBoss'
                    elif 'apache' in source.lower():
                        app_name = 'Apache'
                    else:
                        app_name = host or 'Unknown'
                
                # Log seviyesini belirle
                raw_message = result.get('_raw', '')
                if 'FATAL' in raw_message or 'HTTP 5' in raw_message:
                    log_level = 'CRITICAL'
                elif 'ERROR' in raw_message:
                    log_level = 'ERROR'
                elif 'HTTP 4' in raw_message:
                    log_level = 'WARNING'
                else:
                    log_level = 'ERROR'
                
                logs.append({
                    'timestamp': result.get('_time', ''),
                    'log_level': log_level,
                    'message': raw_message[:500],  # İlk 500 karakter
                    'application_name': app_name,
                    'host_name': result.get('host', ''),
                    'source_platform': 'splunk',
                    'deep_link_url': deep_link,
                    'metadata': {
                        'source': result.get('source', ''),
                        'index': result.get('index', ''),
                    }
                })
            
            return logs
        
        return cache.get_or_set(cache_key, fetch_error_logs, 300)
    
    def get_application_metrics(self, application_name: str, time_range: str = '24h') -> Dict:
        """Uygulama metriklerini getir"""
        cache_key = f"splunk_metrics_{application_name}_{time_range}"
        
        def fetch_metrics():
            metrics = {}
            
            # Request count
            query = f'search index=* source="*{application_name}*" | stats count by _time | timechart span=1h count'
            data = self._make_search_request(query, f'-{time_range}')
            if data and 'results' in data:
                metrics['request_count'] = len(data['results'])
            
            # Error count
            error_query = f'search index=* source="*{application_name}*" (ERROR OR FATAL) | stats count'
            error_data = self._make_search_request(error_query, f'-{time_range}')
            if error_data and 'results' in error_data and error_data['results']:
                metrics['error_count'] = int(error_data['results'][0].get('count', 0))
            else:
                metrics['error_count'] = 0
            
            # Response time (eğer log'larda varsa)
            response_query = f'search index=* source="*{application_name}*" "response_time" | stats avg(response_time) as avg_response_time'
            response_data = self._make_search_request(response_query, f'-{time_range}')
            if response_data and 'results' in response_data and response_data['results']:
                metrics['avg_response_time'] = float(response_data['results'][0].get('avg_response_time', 0))
            else:
                metrics['avg_response_time'] = 0
            
            return metrics
        
        return cache.get_or_set(cache_key, fetch_metrics, 300)
    
    def get_dashboard_summary(self, time_range: str = '24h') -> Dict:
        """Dashboard özet bilgilerini getir"""
        cache_key = f"splunk_dashboard_summary_{time_range}"
        
        def fetch_summary():
            summary = {
                'total_logs': 0,
                'error_logs': 0,
                'warning_logs': 0,
                'applications': [],
                'top_errors': []
            }
            
            # Toplam log sayısı
            total_query = 'search index=* | stats count'
            total_data = self._make_search_request(total_query, f'-{time_range}')
            if total_data and 'results' in total_data and total_data['results']:
                summary['total_logs'] = int(total_data['results'][0].get('count', 0))
            
            # Hata log sayısı
            error_query = 'search index=* (ERROR OR FATAL) | stats count'
            error_data = self._make_search_request(error_query, f'-{time_range}')
            if error_data and 'results' in error_data and error_data['results']:
                summary['error_logs'] = int(error_data['results'][0].get('count', 0))
            
            # Uyarı log sayısı
            warning_query = 'search index=* (WARNING OR WARN) | stats count'
            warning_data = self._make_search_request(warning_query, f'-{time_range}')
            if warning_data and 'results' in warning_data and warning_data['results']:
                summary['warning_logs'] = int(warning_data['results'][0].get('count', 0))
            
            # En çok hata veren uygulamalar
            app_query = 'search index=* (ERROR OR FATAL) | stats count by source | sort -count | head 10'
            app_data = self._make_search_request(app_query, f'-{time_range}')
            if app_data and 'results' in app_data:
                summary['applications'] = app_data['results']
            
            return summary
        
        return cache.get_or_set(cache_key, fetch_summary, 300)
