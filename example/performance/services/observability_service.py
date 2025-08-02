import asyncio
import concurrent.futures
from typing import Dict, List, Any
from django.core.cache import cache
from django.utils import timezone
from .dynatrace import DynatraceService
from .splunk_service import SplunkService
from .kibana_service import KibanaService
from .instana_service import InstanaService
import logging

logger = logging.getLogger(__name__)

class ObservabilityService:
    """Birleşik observability servisi - tüm platformları koordine eder"""
    
    def __init__(self):
        self.dynatrace = DynatraceService()
        self.splunk = SplunkService()
        self.kibana = KibanaService()
        self.instana = InstanaService()
    
    def get_unified_error_logs(self, application_name: str = None, time_range: str = '24h') -> Dict:
        """Tüm platformlardan hata loglarını birleşik olarak getir"""
        cache_key = f"unified_errors_{application_name or 'all'}_{time_range}"
        
        def fetch_unified_logs():
            # Paralel olarak tüm servisleri çağır
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Future'ları başlat
                splunk_future = executor.submit(self.splunk.get_error_logs, application_name, time_range)
                kibana_future = executor.submit(self.kibana.get_error_logs, application_name, time_range)
                instana_future = executor.submit(self.instana.get_error_logs, application_name, time_range)
                
                # Sonuçları topla
                results = {
                    'splunk_logs': [],
                    'kibana_logs': [],
                    'instana_logs': [],
                    'all_logs': [],
                    'summary': {
                        'total_logs': 0,
                        'by_platform': {},
                        'by_level': {},
                        'by_application': {},
                        'timeline': []
                    }
                }
                
                try:
                    results['splunk_logs'] = splunk_future.result(timeout=30) or []
                except Exception as e:
                    logger.error(f"Splunk error logs fetch failed: {str(e)}")
                
                try:
                    results['kibana_logs'] = kibana_future.result(timeout=30) or []
                except Exception as e:
                    logger.error(f"Kibana error logs fetch failed: {str(e)}")
                
                try:
                    results['instana_logs'] = instana_future.result(timeout=30) or []
                except Exception as e:
                    logger.error(f"Instana error logs fetch failed: {str(e)}")
            
            # Tüm logları birleştir
            all_logs = (
                results['splunk_logs'] + 
                results['kibana_logs'] + 
                results['instana_logs']
            )
            
            # Zaman sırasına göre sırala
            all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            results['all_logs'] = all_logs
            
            # Özet istatistikleri hesapla
            results['summary'] = self._calculate_log_summary(all_logs)
            
            return results
        
        return cache.get_or_set(cache_key, fetch_unified_logs, 300)
    
    def get_unified_dashboard_summary(self, time_range: str = '24h') -> Dict:
        """Tüm platformlardan dashboard özet bilgilerini getir"""
        cache_key = f"unified_dashboard_summary_{time_range}"
        
        def fetch_unified_summary():
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # Future'ları başlat
                splunk_future = executor.submit(self.splunk.get_dashboard_summary, time_range)
                kibana_future = executor.submit(self.kibana.get_dashboard_summary, time_range)
                instana_future = executor.submit(self.instana.get_dashboard_summary, time_range)
                
                # Sonuçları topla
                summaries = {}
                
                try:
                    summaries['splunk'] = splunk_future.result(timeout=30) or {}
                except Exception as e:
                    logger.error(f"Splunk summary fetch failed: {str(e)}")
                    summaries['splunk'] = {}
                
                try:
                    summaries['kibana'] = kibana_future.result(timeout=30) or {}
                except Exception as e:
                    logger.error(f"Kibana summary fetch failed: {str(e)}")
                    summaries['kibana'] = {}
                
                try:
                    summaries['instana'] = instana_future.result(timeout=30) or {}
                except Exception as e:
                    logger.error(f"Instana summary fetch failed: {str(e)}")
                    summaries['instana'] = {}
            
            # Birleşik özet oluştur
            unified_summary = {
                'total_logs': (
                    summaries.get('splunk', {}).get('total_logs', 0) +
                    summaries.get('kibana', {}).get('total_logs', 0)
                ),
                'total_errors': (
                    summaries.get('splunk', {}).get('error_logs', 0) +
                    summaries.get('kibana', {}).get('error_logs', 0) +
                    summaries.get('instana', {}).get('total_errors', 0)
                ),
                'total_requests': summaries.get('instana', {}).get('total_requests', 0),
                'avg_response_time': summaries.get('instana', {}).get('avg_response_time', 0),
                'error_rate': 0,
                'platform_breakdown': {
                    'splunk': {
                        'logs': summaries.get('splunk', {}).get('total_logs', 0),
                        'errors': summaries.get('splunk', {}).get('error_logs', 0),
                        'status': 'connected' if summaries.get('splunk') else 'disconnected'
                    },
                    'kibana': {
                        'logs': summaries.get('kibana', {}).get('total_logs', 0),
                        'errors': summaries.get('kibana', {}).get('error_logs', 0),
                        'status': 'connected' if summaries.get('kibana') else 'disconnected'
                    },
                    'instana': {
                        'requests': summaries.get('instana', {}).get('total_requests', 0),
                        'errors': summaries.get('instana', {}).get('total_errors', 0),
                        'status': 'connected' if summaries.get('instana') else 'disconnected'
                    }
                },
                'top_applications': self._merge_top_applications(summaries),
                'status_codes': summaries.get('kibana', {}).get('status_codes', []),
                'raw_summaries': summaries
            }
            
            # Error rate hesapla
            if unified_summary['total_requests'] > 0:
                unified_summary['error_rate'] = (
                    unified_summary['total_errors'] / unified_summary['total_requests'] * 100
                )
            
            return unified_summary
        
        return cache.get_or_set(cache_key, fetch_unified_summary, 300)
    
    def get_application_health_score(self, application_name: str, time_range: str = '24h') -> Dict:
        """Uygulama sağlık skoru hesapla"""
        cache_key = f"app_health_{application_name}_{time_range}"
        
        def calculate_health_score():
            # Tüm platformlardan metrik al
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                splunk_future = executor.submit(self.splunk.get_application_metrics, application_name, time_range)
                kibana_future = executor.submit(self.kibana.get_application_metrics, application_name, time_range)
                instana_future = executor.submit(self.instana.get_application_metrics, application_name, time_range)
                
                metrics = {}
                try:
                    metrics['splunk'] = splunk_future.result(timeout=30) or {}
                except:
                    metrics['splunk'] = {}
                
                try:
                    metrics['kibana'] = kibana_future.result(timeout=30) or {}
                except:
                    metrics['kibana'] = {}
                
                try:
                    metrics['instana'] = instana_future.result(timeout=30) or {}
                except:
                    metrics['instana'] = {}
            
            # Sağlık skoru hesapla (0-100)
            health_score = 100
            factors = []
            
            # Error rate faktörü
            total_requests = (
                metrics.get('splunk', {}).get('request_count', 0) +
                metrics.get('kibana', {}).get('request_count', 0) +
                metrics.get('instana', {}).get('request_count', 0)
            )
            
            total_errors = (
                metrics.get('splunk', {}).get('error_count', 0) +
                metrics.get('kibana', {}).get('error_count', 0) +
                metrics.get('instana', {}).get('error_count', 0)
            )
            
            if total_requests > 0:
                error_rate = (total_errors / total_requests) * 100
                if error_rate > 10:  # %10'dan fazla hata
                    error_penalty = min(50, error_rate * 2)  # Maksimum 50 puan ceza
                    health_score -= error_penalty
                    factors.append(f"Yüksek hata oranı: %{error_rate:.1f}")
            
            # Response time faktörü
            avg_response_times = [
                metrics.get('splunk', {}).get('avg_response_time', 0),
                metrics.get('kibana', {}).get('avg_response_time', 0),
                metrics.get('instana', {}).get('avg_response_time', 0)
            ]
            
            valid_response_times = [rt for rt in avg_response_times if rt > 0]
            if valid_response_times:
                avg_response_time = sum(valid_response_times) / len(valid_response_times)
                if avg_response_time > 2000:  # 2 saniyeden fazla
                    response_penalty = min(30, (avg_response_time - 2000) / 100)
                    health_score -= response_penalty
                    factors.append(f"Yavaş yanıt süresi: {avg_response_time:.0f}ms")
            
            # Minimum 0, maksimum 100
            health_score = max(0, min(100, health_score))
            
            # Sağlık durumu kategorisi
            if health_score >= 90:
                health_status = 'excellent'
                health_color = 'success'
            elif health_score >= 70:
                health_status = 'good'
                health_color = 'info'
            elif health_score >= 50:
                health_status = 'warning'
                health_color = 'warning'
            else:
                health_status = 'critical'
                health_color = 'danger'
            
            return {
                'application_name': application_name,
                'health_score': round(health_score, 1),
                'health_status': health_status,
                'health_color': health_color,
                'factors': factors,
                'metrics': {
                    'total_requests': total_requests,
                    'total_errors': total_errors,
                    'error_rate': (total_errors / total_requests * 100) if total_requests > 0 else 0,
                    'avg_response_time': sum(valid_response_times) / len(valid_response_times) if valid_response_times else 0
                },
                'platform_metrics': metrics
            }
        
        return cache.get_or_set(cache_key, calculate_health_score, 300)
    
    def _calculate_log_summary(self, logs: List[Dict]) -> Dict:
        """Log özet istatistiklerini hesapla"""
        summary = {
            'total_logs': len(logs),
            'by_platform': {},
            'by_level': {},
            'by_application': {},
            'timeline': []
        }
        
        for log in logs:
            # Platform bazlı sayım
            platform = log.get('source_platform', 'unknown')
            summary['by_platform'][platform] = summary['by_platform'].get(platform, 0) + 1
            
            # Seviye bazlı sayım
            level = log.get('log_level', 'UNKNOWN')
            summary['by_level'][level] = summary['by_level'].get(level, 0) + 1
            
            # Uygulama bazlı sayım
            app = log.get('application_name', 'Unknown')
            summary['by_application'][app] = summary['by_application'].get(app, 0) + 1
        
        return summary
    
    def _merge_top_applications(self, summaries: Dict) -> List[Dict]:
        """Farklı platformlardan gelen top application listelerini birleştir"""
        app_errors = {}
        
        # Splunk'tan uygulamaları al
        for app in summaries.get('splunk', {}).get('applications', []):
            app_name = app.get('source', '').split('/')[-1] or 'Unknown'
            app_errors[app_name] = app_errors.get(app_name, 0) + app.get('count', 0)
        
        # Kibana'dan uygulamaları al
        for app in summaries.get('kibana', {}).get('applications', []):
            app_name = app.get('key', 'Unknown')
            app_errors[app_name] = app_errors.get(app_name, 0) + app.get('error_count', 0)
        
        # Instana'dan uygulamaları al
        for app in summaries.get('instana', {}).get('applications', []):
            app_name = app.get('name', 'Unknown')
            app_errors[app_name] = app_errors.get(app_name, 0) + app.get('error_count', 0)
        
        # Sırala ve döndür
        sorted_apps = sorted(
            [{'name': name, 'error_count': count} for name, count in app_errors.items()],
            key=lambda x: x['error_count'],
            reverse=True
        )
        
        return sorted_apps[:10]
