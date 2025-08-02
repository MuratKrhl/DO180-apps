from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Max
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
import json
import csv

from .models import Server, Application, OperationHistory, Certificate
from .forms import ServerForm, ApplicationForm, OperationHistoryForm, CertificateForm, InventoryFilterForm

class InventoryListView(LoginRequiredMixin, ListView):
    """Ana envanter listesi - Birleşik görünüm"""
    template_name = 'inventory/inventory_list.html'
    context_object_name = 'applications'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Application.objects.filter(is_active=True).select_related('server')
        
        # Filtreleme parametreleri
        search = self.request.GET.get('search')
        environment = self.request.GET.get('environment')
        app_type = self.request.GET.get('app_type')
        status = self.request.GET.get('status')
        migration_status = self.request.GET.get('migration_status')
        version = self.request.GET.get('version')  # JBoss 8 filtresi için
        criticality = self.request.GET.get('criticality')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(server__hostname__icontains=search) |
                Q(version__icontains=search)
            )
        
        if environment:
            queryset = queryset.filter(server__environment=environment)
        
        if app_type:
            queryset = queryset.filter(application_type=app_type)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if migration_status:
            queryset = queryset.filter(migration_status=migration_status)
        
        if criticality:
            queryset = queryset.filter(criticality=criticality)
        
        # JBoss 8 özel filtresi
        if version == 'jboss8':
            queryset = queryset.filter(
                application_type='jboss',
                version__icontains='8'
            )
        
        # Sıralama
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by in ['name', '-name', 'server__hostname', '-server__hostname', 
                       'status', '-status', 'last_check', '-last_check']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtreleme formu
        context['filter_form'] = InventoryFilterForm(self.request.GET)
        
        # İstatistikler
        total_apps = Application.objects.filter(is_active=True).count()
        context['stats'] = {
            'total_applications': total_apps,
            'running_applications': Application.objects.filter(is_active=True, status='running').count(),
            'error_applications': Application.objects.filter(is_active=True, status='error').count(),
            'jboss8_applications': Application.objects.filter(
                is_active=True, 
                application_type='jboss',
                version__icontains='8'
            ).count(),
        }
        
        # Ortam dağılımı
        context['environment_stats'] = Application.objects.filter(is_active=True).values(
            'server__environment'
        ).annotate(count=Count('id')).order_by('server__environment')
        
        # Uygulama tipi dağılımı
        context['type_stats'] = Application.objects.filter(is_active=True).values(
            'application_type'
        ).annotate(count=Count('id')).order_by('application_type')
        
        # Aktif filtreler
        context['active_filters'] = {
            'search': self.request.GET.get('search', ''),
            'environment': self.request.GET.get('environment', ''),
            'app_type': self.request.GET.get('app_type', ''),
            'status': self.request.GET.get('status', ''),
            'migration_status': self.request.GET.get('migration_status', ''),
            'version': self.request.GET.get('version', ''),
            'criticality': self.request.GET.get('criticality', ''),
        }
        
        return context

class ApplicationDetailView(LoginRequiredMixin, DetailView):
    """Uygulama detay sayfası - Sekmeli görünüm"""
    model = Application
    template_name = 'inventory/application_detail.html'
    context_object_name = 'application'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_object()
        
        # Operasyon geçmişi
        context['operation_history'] = application.operation_history.all()[:10]
        
        # Sertifikalar
        context['certificates'] = application.certificates.all()
        
        # İlgili AskGT makaleleri (örnek)
        from askgt.models import Question
        context['related_questions'] = Question.objects.filter(
            Q(title__icontains=application.name) |
            Q(content__icontains=application.application_type),
            is_active=True
        )[:5]
        
        # Performans metrikleri (son 24 saat)
        # Bu kısım performance modülü ile entegre edilecek
        context['performance_metrics'] = {
            'avg_response_time': application.response_time or 0,
            'uptime_percentage': 99.5,  # Örnek veri
            'last_downtime': None,
        }
        
        # Benzer uygulamalar
        context['similar_applications'] = Application.objects.filter(
            application_type=application.application_type,
            is_active=True
        ).exclude(id=application.id)[:5]
        
        return context

class ServerListView(LoginRequiredMixin, ListView):
    """Sunucu listesi"""
    model = Server
    template_name = 'inventory/server_list.html'
    context_object_name = 'servers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Server.objects.filter(is_active=True)
        
        # Filtreleme
        search = self.request.GET.get('search')
        environment = self.request.GET.get('environment')
        os_filter = self.request.GET.get('os')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(
                Q(hostname__icontains=search) |
                Q(ip_address__icontains=search) |
                Q(description__icontains=search)
            )
        
        if environment:
            queryset = queryset.filter(environment=environment)
        
        if os_filter:
            queryset = queryset.filter(operating_system=os_filter)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('hostname')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtreleme seçenekleri
        context['environment_choices'] = Server.ENVIRONMENT_CHOICES
        context['os_choices'] = Server.OS_CHOICES
        context['status_choices'] = Server.STATUS_CHOICES
        
        # Aktif filtreler
        context['active_filters'] = {
            'search': self.request.GET.get('search', ''),
            'environment': self.request.GET.get('environment', ''),
            'os': self.request.GET.get('os', ''),
            'status': self.request.GET.get('status', ''),
        }
        
        return context

class ServerDetailView(LoginRequiredMixin, DetailView):
    """Sunucu detay sayfası"""
    model = Server
    template_name = 'inventory/server_detail.html'
    context_object_name = 'server'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        server = self.get_object()
        
        # Sunucudaki uygulamalar
        context['applications'] = server.applications.filter(is_active=True)
        
        # Sunucu istatistikleri
        context['app_stats'] = {
            'total': server.applications.filter(is_active=True).count(),
            'running': server.applications.filter(is_active=True, status='running').count(),
            'stopped': server.applications.filter(is_active=True, status='stopped').count(),
            'error': server.applications.filter(is_active=True, status='error').count(),
        }
        
        return context

# CRUD Views - Admin yetkisi gerekli
class ApplicationCreateView(PermissionRequiredMixin, CreateView):
    """Uygulama ekleme"""
    model = Application
    form_class = ApplicationForm
    template_name = 'inventory/application_form.html'
    permission_required = 'inventory.add_application'
    success_url = reverse_lazy('inventory:inventory_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Uygulama başarıyla eklendi.')
        return super().form_valid(form)

class ApplicationUpdateView(PermissionRequiredMixin, UpdateView):
    """Uygulama düzenleme"""
    model = Application
    form_class = ApplicationForm
    template_name = 'inventory/application_form.html'
    permission_required = 'inventory.change_application'
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, 'Uygulama başarıyla güncellendi.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('inventory:application_detail', kwargs={'pk': self.object.pk})

class ApplicationDeleteView(PermissionRequiredMixin, DeleteView):
    """Uygulama silme"""
    model = Application
    template_name = 'inventory/application_confirm_delete.html'
    permission_required = 'inventory.delete_application'
    success_url = reverse_lazy('inventory:inventory_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Uygulama başarıyla silindi.')
        return super().delete(request, *args, **kwargs)

# AJAX Views
@login_required
def check_application_status(request, pk):
    """Uygulama durumunu kontrol et"""
    application = get_object_or_404(Application, pk=pk)
    
    if request.method == 'POST':
        status = application.check_status()
        return JsonResponse({
            'success': True,
            'status': application.status,
            'status_display': application.get_status_display(),
            'status_color': application.status_color,
            'response_time': application.response_time,
            'last_check': application.last_check.isoformat() if application.last_check else None
        })
    
    return JsonResponse({'success': False})

@login_required
def bulk_status_check(request):
    """Toplu durum kontrolü"""
    if request.method == 'POST':
        app_ids = request.POST.getlist('application_ids')
        applications = Application.objects.filter(id__in=app_ids, is_active=True)
        
        results = []
        for app in applications:
            app.check_status()
            results.append({
                'id': app.id,
                'name': app.name,
                'status': app.status,
                'status_display': app.get_status_display(),
                'status_color': app.status_color,
                'response_time': app.response_time
            })
        
        return JsonResponse({'success': True, 'results': results})
    
    return JsonResponse({'success': False})

@login_required
def export_inventory(request):
    """Envanter dışa aktarma"""
    format_type = request.GET.get('format', 'csv')
    
    applications = Application.objects.filter(is_active=True).select_related('server')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Uygulama Adı', 'Tip', 'Versiyon', 'Sunucu', 'IP', 'Port', 
            'Ortam', 'Durum', 'Migrasyon Durumu', 'Kritiklik'
        ])
        
        for app in applications:
            writer.writerow([
                app.name, app.get_application_type_display(), app.version,
                app.server.hostname, app.server.ip_address, app.port,
                app.server.get_environment_display(), app.get_status_display(),
                app.get_migration_status_display(), app.get_criticality_display()
            ])
        
        return response
    
    return JsonResponse({'error': 'Desteklenmeyen format'})

# Dashboard API Views
@login_required
def inventory_stats_api(request):
    """Envanter istatistikleri API"""
    stats = {
        'total_applications': Application.objects.filter(is_active=True).count(),
        'total_servers': Server.objects.filter(is_active=True).count(),
        'running_applications': Application.objects.filter(is_active=True, status='running').count(),
        'error_applications': Application.objects.filter(is_active=True, status='error').count(),
        'jboss8_applications': Application.objects.filter(
            is_active=True, 
            application_type='jboss',
            version__icontains='8'
        ).count(),
        'total_jboss_applications': Application.objects.filter(
            is_active=True, 
            application_type='jboss'
        ).count(),
    }
    
    # JBoss 8 migrasyon yüzdesi
    if stats['total_jboss_applications'] > 0:
        stats['jboss8_percentage'] = round(
            (stats['jboss8_applications'] / stats['total_jboss_applications']) * 100, 1
        )
    else:
        stats['jboss8_percentage'] = 0
    
    return JsonResponse(stats)
