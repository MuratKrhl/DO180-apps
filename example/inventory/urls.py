from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Ana envanter listesi
    path('', views.InventoryListView.as_view(), name='inventory_list'),
    
    # Sunucular
    path('servers/', views.ServerListView.as_view(), name='server_list'),
    path('servers/<int:pk>/', views.ServerDetailView.as_view(), name='server_detail'),
    
    # Uygulamalar
    path('applications/', views.InventoryListView.as_view(), name='application_list'),
    path('applications/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('applications/add/', views.ApplicationCreateView.as_view(), name='application_add'),
    path('applications/<int:pk>/edit/', views.ApplicationUpdateView.as_view(), name='application_edit'),
    path('applications/<int:pk>/delete/', views.ApplicationDeleteView.as_view(), name='application_delete'),
    
    # AJAX endpoints
    path('api/applications/<int:pk>/check-status/', views.check_application_status, name='check_application_status'),
    path('api/applications/bulk-check/', views.bulk_status_check, name='bulk_status_check'),
    path('api/stats/', views.inventory_stats_api, name='inventory_stats_api'),
    
    # Export
    path('export/', views.export_inventory, name='export_inventory'),
]
