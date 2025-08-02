from django.contrib import admin
from .models import MetricSource, MetricDefinition, Dashboard, DashboardPanel, Alert

@admin.register(MetricSource)
class MetricSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'base_url', 'is_default', 'is_active']
    list_filter = ['source_type', 'is_default', 'is_active']
    search_fields = ['name', 'base_url']

@admin.register(MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'metric_type', 'chart_type', 'source', 'is_active']
    list_filter = ['category', 'metric_type', 'chart_type', 'source', 'is_active']
    search_fields = ['name', 'description']

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_default', 'refresh_interval', 'is_active']
    list_filter = ['is_default', 'is_active']
    search_fields = ['name', 'description']

@admin.register(DashboardPanel)
class DashboardPanelAdmin(admin.ModelAdmin):
    list_display = ['title', 'dashboard', 'metric', 'position_x', 'position_y', 'width', 'height']
    list_filter = ['dashboard']
    search_fields = ['title', 'dashboard__name', 'metric__name']

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'metric', 'severity', 'status', 'triggered_at', 'resolved_at']
    list_filter = ['severity', 'status', 'triggered_at']
    search_fields = ['title', 'description', 'metric__name']
    readonly_fields = ['triggered_at']
