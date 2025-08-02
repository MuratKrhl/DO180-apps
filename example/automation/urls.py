from django.urls import path
from . import views

app_name = 'automation'

urlpatterns = [
    path('', views.automation_list, name='automation_list'),
    path('task/create/', views.task_create, name='task_create'),
    path('task/<int:pk>/', views.task_detail, name='task_detail'),
    path('task/<int:pk>/execute/', views.task_execute, name='task_execute'),
    path('task/<int:pk>/approve/', views.task_approve, name='task_approve'),
    path('playbooks/', views.playbook_list, name='playbook_list'),
    path('execution/<int:pk>/', views.execution_detail, name='execution_detail'),
    
    # API endpoints
    path('api/task/<int:pk>/status/', views.task_status_api, name='task_status_api'),
]
