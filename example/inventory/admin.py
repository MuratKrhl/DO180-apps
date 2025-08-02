from django.contrib import admin
from .models import Server, Application

@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ['hostname', 'ip_address', 'operating_system', 'environment', 'cpu_cores', 'memory_gb', 'is_active']
    list_filter = ['operating_system', 'environment', 'is_active', 'location']
    search_fields = ['hostname', 'ip_address', 'description']
    list_editable = ['is_active']

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['name', 'application_type', 'version', 'server', 'port', 'is_active']
    list_filter = ['application_type', 'is_active', 'server__environment']
    search_fields = ['name', 'description', 'server__hostname']
    list_editable = ['is_active']
    raw_id_fields = ['server']
