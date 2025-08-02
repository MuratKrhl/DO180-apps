from django.urls import path
from . import views

app_name = 'askgt'

urlpatterns = [
    # Ana sayfa - tüm dokümanlar
    path('', views.AllDocumentsListView.as_view(), name='document_list'),
    
    # Kategori bazlı doküman listesi
    path('category/<slug:category_slug>/', views.CategoryDocumentListView.as_view(), name='category_documents'),
    
    # Doküman yönlendirme
    path('document/<int:pk>/', views.DocumentRedirectView.as_view(), name='document_redirect'),
    
    # Soru-Cevap sistemi (mevcut)
    path('questions/', views.question_list, name='question_list'),
    path('question/<int:pk>/', views.question_detail, name='question_detail'),
    path('categories/', views.category_list, name='category_list'),
    
    # API endpoints
    path('api/search/', views.document_search_api, name='document_search_api'),
    
    # Yönetim paneli
    path('manage/', views.manage_dashboard, name='manage_dashboard'),
    path('manage/question/create/', views.question_create, name='question_create'),
    path('manage/question/<int:pk>/edit/', views.question_edit, name='question_edit'),
    path('manage/question/<int:pk>/delete/', views.question_delete, name='question_delete'),
    path('manage/category/create/', views.category_create, name='category_create'),
    path('manage/category/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('manage/category/<int:pk>/delete/', views.category_delete, name='category_delete'),
]
