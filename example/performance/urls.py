from django.urls import path
from . import views

app_name = 'performance'

urlpatterns = [
    # Dashboard views
    path('', views.PerformanceDashboardView.as_view(), name='performance_dashboard'),
    path('technology/<str:technology>/', views.technology_dashboard, name='technology_dashboard'),
    path('metrics/<int:pk>/', views.metric_detail, name='metric_detail'),
    path('observability/', views.ObservabilityDashboardView.as_view(), name='observability_dashboard'),
    
    # API endpoints
    path('api/technology/<str:technology>/metrics/', views.technology_metrics_api, name='technology_metrics_api'),
    path('api/metrics/<int:pk>/data/', views.metric_data_api, name='metric_data_api'),
    path('api/observability/logs/', views.observability_logs_api, name='observability_logs_api'),
    path('api/observability/summary/', views.observability_summary_api, name='observability_summary_api'),
    path('api/application/<str:application_name>/health/', views.application_health_api, name='application_health_api'),
    path('api/technologies/', views.technology_list_api, name='technology_list_api'),
    path('api/alerts/<int:pk>/acknowledge/', views.alert_acknowledge, name='alert_acknowledge'),
]
