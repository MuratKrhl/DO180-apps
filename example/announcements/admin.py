from django.contrib import admin
from .models import Announcement

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'announcement_type', 'is_pinned', 'is_urgent', 'start_date', 'end_date', 'is_active']
    list_filter = ['announcement_type', 'is_pinned', 'is_urgent', 'is_active', 'start_date']
    search_fields = ['title', 'content']
    list_editable = ['is_pinned', 'is_urgent', 'is_active']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('title', 'content', 'announcement_type')
        }),
        ('Görünürlük Ayarları', {
            'fields': ('is_pinned', 'is_urgent', 'is_active')
        }),
        ('Tarih Ayarları', {
            'fields': ('start_date', 'end_date')
        }),
        ('Hedefleme', {
            'fields': ('target_audience',)
        }),
    )
