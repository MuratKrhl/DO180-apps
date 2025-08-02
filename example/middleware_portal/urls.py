from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication
    path('auth/', include('authentication.urls')),
    
    # Core (Dashboard)
    path('', include('core.urls')),
    
    # Modules
    path('inventory/', include('inventory.urls')),
    path('certificates/', include('certificates.urls')),
    path('askgt/', include('askgt.urls')),
    path('announcements/', include('announcements.urls')),
    path('automation/', include('automation.urls')),
    path('performance/', include('performance.urls')),
]

# Static files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "Middleware Portal Yönetimi"
admin.site.site_title = "Middleware Portal"
admin.site.index_title = "Yönetim Paneli"
