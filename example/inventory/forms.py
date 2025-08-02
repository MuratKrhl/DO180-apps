from django import forms
from django.core.exceptions import ValidationError
from .models import Server, Application, OperationHistory, Certificate

class ServerForm(forms.ModelForm):
    """Sunucu formu"""
    class Meta:
        model = Server
        fields = [
            'hostname', 'ip_address', 'operating_system', 'environment', 'status',
            'cpu_cores', 'memory_gb', 'disk_gb', 'location', 'description'
        ]
        widgets = {
            'hostname': forms.TextInput(attrs={'class': 'form-control'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control'}),
            'operating_system': forms.Select(attrs={'class': 'form-select'}),
            'environment': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'cpu_cores': forms.NumberInput(attrs={'class': 'form-control'}),
            'memory_gb': forms.NumberInput(attrs={'class': 'form-control'}),
            'disk_gb': forms.NumberInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ApplicationForm(forms.ModelForm):
    """Uygulama formu"""
    class Meta:
        model = Application
        fields = [
            'name', 'application_type', 'version', 'server', 'port', 'context_path',
            'config_path', 'log_path', 'startup_script', 'description', 'status',
            'migration_status', 'target_version', 'migration_date', 'migration_notes',
            'ssl_enabled', 'certificate_expiry', 'criticality', 'maintenance_window'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'application_type': forms.Select(attrs={'class': 'form-select'}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'server': forms.Select(attrs={'class': 'form-select'}),
            'port': forms.NumberInput(attrs={'class': 'form-control'}),
            'context_path': forms.TextInput(attrs={'class': 'form-control'}),
            'config_path': forms.TextInput(attrs={'class': 'form-control'}),
            'log_path': forms.TextInput(attrs={'class': 'form-control'}),
            'startup_script': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'migration_status': forms.Select(attrs={'class': 'form-select'}),
            'target_version': forms.TextInput(attrs={'class': 'form-control'}),
            'migration_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'migration_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ssl_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'certificate_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'criticality': forms.Select(attrs={'class': 'form-select'}),
            'maintenance_window': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def clean_port(self):
        port = self.cleaned_data['port']
        server = self.cleaned_data.get('server')
        
        if server and port:
            # Aynı sunucuda aynı port kontrolü
            existing = Application.objects.filter(
                server=server, 
                port=port,
                is_active=True
            )
            
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(
                    f'Bu sunucuda {port} portu zaten kullanılıyor.'
                )
        
        return port

class OperationHistoryForm(forms.ModelForm):
    """Operasyon geçmişi formu"""
    class Meta:
        model = OperationHistory
        fields = ['application', 'operation_type', 'description']
        widgets = {
            'application': forms.Select(attrs={'class': 'form-select'}),
            'operation_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class CertificateForm(forms.ModelForm):
    """Sertifika formu"""
    class Meta:
        model = Certificate
        fields = [
            'name', 'cert_type', 'application', 'issuer', 'subject', 
            'serial_number', 'issue_date', 'expiry_date', 'fingerprint'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'cert_type': forms.Select(attrs={'class': 'form-select'}),
            'application': forms.Select(attrs={'class': 'form-select'}),
            'issuer': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fingerprint': forms.TextInput(attrs={'class': 'form-control'}),
        }

class InventoryFilterForm(forms.Form):
    """Envanter filtreleme formu"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Uygulama, sunucu veya versiyon ara...'
        })
    )
    
    environment = forms.ChoiceField(
        required=False,
        choices=[('', 'Tüm Ortamlar')] + Server.ENVIRONMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    app_type = forms.ChoiceField(
        required=False,
        choices=[('', 'Tüm Tipler')] + Application.APPLICATION_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Tüm Durumlar')] + Application.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    migration_status = forms.ChoiceField(
        required=False,
        choices=[('', 'Tüm Migrasyon Durumları')] + Application.MIGRATION_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    criticality = forms.ChoiceField(
        required=False,
        choices=[('', 'Tüm Kritiklik Seviyeleri')] + Application.CRITICALITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    version = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Tüm Versiyonlar'),
            ('jboss8', 'JBoss 8'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
