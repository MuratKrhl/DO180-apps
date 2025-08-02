from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Max, Min
from django.utils import timezone
from datetime import timedelta
from .models import (
    TechnologyDashboard, MetricDefinition, MetricData, 
    Alert, MetricSource, ObservabilityLog
)
from .services.dynatrace import DynatraceService
from .services.observability_service import ObservabilityService
import json

class PerformanceDashboardView(LoginRequiredMixin, TemplateView):
    """Ana performans dashboard"""
    template_name = 'performance/performance_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Teknoloji dashboard'larını al
        context['technologies'] = TechnologyDashboard.objects.filter(
            is_active=True
        ).order_by('display_name')
        
        # Öne çıkan teknolojiler
        context['featured_technologies'] = TechnologyDashboard.objects.filter(
            is_active=True, 
            is_featured=True
        ).order_by('display_name')
        
        # Son uyarılar
        context['recent_alerts'] = Alert.objects.filter(
            status='active'
        ).select_related('metric', 'metric__technology').order_by('-triggered_at')[:10]
        
        # Metrik kaynakları durumu
        context['metric_sources'] = MetricSource.objects.filter(is_active=True)
        
        # İstatistikler
        context['stats'] = {
            'total_technologies': TechnologyDashboard.objects.filter(is_active=True).count(),
            'active_alerts': Alert.objects.filter(status='active').count(),
            'critical_alerts': Alert.objects.filter(status='active', severity='critical').count(),
            'total_metrics': MetricDefinition.objects.filter(is_active=True).count(),
        }
        
        return context

@login_required
def technology_dashboard(request, technology):
    """Teknoloji bazlı dashboard"""
    tech_dashboard = get_object_or_404(
        TechnologyDashboard, 
        technology=technology, 
        is_active=True
    )
    
    # Teknolojiye ait metrikler
    metrics = MetricDefinition.objects.filter(
        technology=tech_dashboard,
        is_active=True
    ).order_by('display_order', 'name')
    
    # Ana metrikler (dashboard'da gösterilecek)
    primary_metrics = metrics.filter(is_primary=True)
    
    # Son uyarılar
    recent_alerts = Alert.objects.filter(
        metric__technology=tech_dashboard,
        status='active'
    ).order_by('-triggered_at')[:5]
    
    context = {
        'technology': tech_dashboard,
        'metrics': metrics,
        'primary_metrics': primary_metrics,
        'recent_alerts': recent_alerts,
        'time_ranges': [
            ('1h', 'Son 1 Saat'),
            ('6h', 'Son 6 Saat'),
            ('24h', 'Son 24 Saat'),
            ('7d', 'Son 7 Gün'),
            ('30d', 'Son 30 Gün'),
        ]
    }
    
    return render(request, 'performance/technology_dashboard.html', context)

@login_required
def metric_detail(request, pk):
    """Metrik detayı"""
    metric = get_object_or_404(MetricDefinition, pk=pk, is_active=True)
    
    # Son 24 saatlik veri
    last_24h = timezone.now() - timedelta(hours=24)
    recent_data = MetricData.objects.filter(
        metric=metric,
        timestamp__gte=last_24h
    ).order_by('-timestamp')[:100]
    
    # İstatistikler
    if recent_data:
        values = [data.value for data in recent_data]
        stats = {
            'current': values[0] if values else 0,
            'average': sum(values) / len(values),
            'maximum': max(values),
            'minimum': min(values),
        }
    else:
        stats = {'current': 0, 'average': 0, 'maximum': 0, 'minimum': 0}
    
    # İlgili uyarılar
    alerts = Alert.objects.filter(metric=metric).order_by('-triggered_at')[:10]
    
    context = {
        'metric': metric,
        'recent_data': recent_data,
        'stats': stats,
        'alerts': alerts,
    }
    return render(request, 'performance/metric_detail.html', context)

class ObservabilityDashboardView(LoginRequiredMixin, TemplateView):
    """Birleşik observability dashboard"""
    template_name = 'performance/observability_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Zaman aralığı seçenekleri
        context['time_ranges'] = [
            ('1h', 'Son 1 Saat'),
            ('6h', 'Son 6 Saat'),
            ('24h', 'Son 24 Saat'),
            ('7d', 'Son 7 Gün'),
        ]
        
        # Uygulama listesi (filtreleme için)
        context['applications'] = ObservabilityLog.objects.values_list(
            'application_name', flat=True
        ).distinct().order_by('application_name')
        
        # Platform durumları
        context['platforms'] = [
            {'name': 'Splunk', 'key': 'splunk', 'icon': 'ri-database-2-line'},
            {'name': 'Kibana', 'key': 'kibana', 'icon': 'ri-search-line'},
            {'name': 'Instana', 'key': 'instana', 'icon': 'ri-pulse-line'},
        ]
        
        return context

# API Views
@login_required
def technology_metrics_api(request, technology):
    """Teknoloji metriklerini API olarak döndür"""
    time_range = request.GET.get('range', '1h')
    
    try:
        dynatrace_service = DynatraceService()
        metrics_data = dynatrace_service.get_technology_metrics(technology, time_range)
        
        return JsonResponse({
            'success': True,
            'data': metrics_data,
            'technology': technology,
            'time_range': time_range
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def metric_data_api(request, pk):
    """Metrik verisi API"""
    time_range = request.GET.get('range', '1h')
    metric = get_object_or_404(MetricDefinition, pk=pk)
    
    try:
        # Dynatrace'den veri çek
        dynatrace_service = DynatraceService()
        
        if metric.source.source_type == 'dynatrace':
            # Teknoloji bazlı metrik çek
            tech_metrics = dynatrace_service.get_technology_metrics(
                metric.technology.technology, 
                time_range
            )
            
            metric_data = tech_metrics.get(metric.name.lower().replace(' ', '_'), {})
        else:
            metric_data = {'values': [], 'timestamps': [], 'current': 0, 'average': 0}
        
        return JsonResponse({
            'success': True,
            'data': metric_data,
            'metric': {
                'name': metric.display_name,
                'unit': metric.unit,
                'chart_type': metric.chart_type
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def observability_logs_api(request):
    """Birleşik observability logları API"""
    application_name = request.GET.get('application')
    time_range = request.GET.get('range', '24h')
    
    try:
        observability_service = ObservabilityService()
        logs_data = observability_service.get_unified_error_logs(application_name, time_range)
        
        return JsonResponse({
            'success': True,
            'data': logs_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def observability_summary_api(request):
    """Observability özet API"""
    time_range = request.GET.get('range', '24h')
    
    try:
        observability_service = ObservabilityService()
        summary_data = observability_service.get_unified_dashboard_summary(time_range)
        
        return JsonResponse({
            'success': True,
            'data': summary_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def application_health_api(request, application_name):
    """Uygulama sağlık skoru API"""
    time_range = request.GET.get('range', '24h')
    
    try:
        observability_service = ObservabilityService()
        health_data = observability_service.get_application_health_score(application_name, time_range)
        
        return JsonResponse({
            'success': True,
            'data': health_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def alert_acknowledge(request, pk):
    """Uyarıyı onayla"""
    alert = get_object_or_404(Alert, pk=pk)
    
    if request.method == 'POST':
        alert.status = 'acknowledged'
        alert.acknowledged_by = request.user
        alert.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Uyarı onaylandı'
        })
    
    return JsonResponse({
        'success': False,
        'error': 'POST method required'
    }, status=405)

@login_required
def technology_list_api(request):
    """Teknoloji listesi API"""
    technologies = TechnologyDashboard.objects.filter(is_active=True).values(
        'id', 'technology', 'display_name', 'icon_class', 'color_scheme'
    )
    
    return JsonResponse({
        'success': True,
        'data': list(technologies)
    })
