from django.urls import path
from . import views

app_name = 'announcements'

urlpatterns = [
    # Liste ve detay
    path('', views.AnnouncementListView.as_view(), name='announcement_list'),
    path('<int:pk>/', views.AnnouncementDetailView.as_view(), name='announcement_detail'),
    
    # CRUD işlemleri
    path('create/', views.AnnouncementCreateView.as_view(), name='announcement_create'),
    path('<int:pk>/edit/', views.AnnouncementUpdateView.as_view(), name='announcement_edit'),
    path('<int:pk>/delete/', views.AnnouncementDeleteView.as_view(), name='announcement_delete'),
    
    # Hızlı işlemler
    path('quick-create/', views.announcement_quick_create, name='announcement_quick_create'),
    path('bulk-action/', views.announcement_bulk_action, name='announcement_bulk_action'),
    
    # Yorumlar
    path('<int:pk>/comment/', views.announcement_comment_create, name='announcement_comment_create'),
    
    # Dashboard ve yönetim
    path('dashboard/', views.announcement_dashboard, name='announcement_dashboard'),
    
    # API endpoints
    path('api/list/', views.announcement_api_list, name='announcement_api_list'),
]
