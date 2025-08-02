from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('terminate-session/<int:session_id>/', views.terminate_session, name='terminate_session'),
    
    # Development only
    path('ldap-test/', views.ldap_test_view, name='ldap_test'),
]
