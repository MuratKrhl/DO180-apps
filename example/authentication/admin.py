from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, LoginAttempt, UserSession

# Inline UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profil Bilgileri'

# Extended User Admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'groups')

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['username', 'ip_address', 'success', 'timestamp']
    list_filter = ['success', 'timestamp']
    search_fields = ['username', 'ip_address']
    readonly_fields = ['username', 'ip_address', 'user_agent', 'success', 'failure_reason', 'timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'created_at', 'last_activity', 'is_active']
    list_filter = ['is_active', 'created_at', 'last_activity']
    search_fields = ['user__username', 'ip_address']
    readonly_fields = ['user', 'session_key', 'ip_address', 'user_agent', 'created_at']
    
    actions = ['terminate_sessions']
    
    def terminate_sessions(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} oturum sonlandırıldı.')
    terminate_sessions.short_description = "Seçili oturumları sonlandır"
