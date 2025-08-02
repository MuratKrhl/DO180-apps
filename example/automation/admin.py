from django.contrib import admin
from .models import AutomationTask

@admin.register(AutomationTask)
class AutomationTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
