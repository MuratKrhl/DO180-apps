from django.contrib import admin
from .models import Category, Question, Document, APISource, DocumentAccess

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'color', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'color']
    search_fields = ['name', 'description']
    list_editable = ['order', 'is_active', 'color']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'priority', 'is_featured', 'view_count', 'is_active']
    list_filter = ['category', 'priority', 'is_featured', 'is_active', 'created_at']
    search_fields = ['title', 'question', 'answer', 'tags']
    list_editable = ['priority', 'is_featured', 'is_active']
    raw_id_fields = ['category']
    readonly_fields = ['view_count']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'document_type', 'source_type', 'view_count', 'is_featured', 'is_active']
    list_filter = ['category', 'document_type', 'source_type', 'is_featured', 'is_active', 'created_at']
    search_fields = ['title', 'summary', 'tags', 'source_id']
    list_editable = ['is_featured', 'is_active']
    raw_id_fields = ['category']
    readonly_fields = ['view_count', 'sync_date', 'source_id']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('title', 'summary', 'original_url', 'category', 'document_type')
        }),
        ('Kaynak Bilgileri', {
            'fields': ('source_type', 'source_id', 'author', 'last_modified', 'sync_date')
        }),
        ('Metadata', {
            'fields': ('tags', 'language', 'content_preview')
        }),
        ('Durum', {
            'fields': ('is_featured', 'is_external', 'is_active', 'view_count')
        }),
    )

@admin.register(APISource)
class APISourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'sync_enabled', 'sync_interval', 'last_sync', 'is_active']
    list_filter = ['sync_enabled', 'is_active', 'last_sync']
    search_fields = ['name', 'api_url']
    list_editable = ['sync_enabled', 'is_active']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'api_url')
        }),
        ('Kimlik Doğrulama', {
            'fields': ('api_key', 'username', 'password')
        }),
        ('Senkronizasyon', {
            'fields': ('sync_enabled', 'sync_interval', 'last_sync')
        }),
        ('Alan Eşleştirme', {
            'fields': ('title_field', 'url_field', 'category_field', 'summary_field')
        }),
        ('Durum', {
            'fields': ('is_active',)
        }),
    )

@admin.register(DocumentAccess)
class DocumentAccessAdmin(admin.ModelAdmin):
    list_display = ['document', 'user', 'accessed_at', 'ip_address']
    list_filter = ['accessed_at']
    search_fields = ['document__title', 'user__username', 'ip_address']
    readonly_fields = ['document', 'user', 'accessed_at', 'ip_address', 'user_agent']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
