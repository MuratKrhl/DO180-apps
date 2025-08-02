from django.apps import AppConfig

class AnsibleIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ansible_integration'
    verbose_name = 'Ansible Entegrasyonu'
    
    def ready(self):
        import ansible_integration.signals
