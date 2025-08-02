from django import forms
from django.contrib.auth.models import User
from .models import CertificateNotificationSettings, KdbCertificate, JavaCertificate

class CertificateFilterForm(forms.Form):
    """Sertifika filtreleme formu"""
    
    EXPIRY_STATUS_CHOICES = [
        ('', 'Tüm Durumlar'),
        ('expired', 'Süresi Dolmuş'),
        ('expiring_7', '7 Gün İçinde'),
        ('expiring_30', '30 Gün İçinde'),
        ('valid', 'Geçerli'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Common Name, Serial, Sunucu ara...'
        })
    )
    
    expiry_status = forms.ChoiceField(
        choices=EXPIRY_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class NotificationSettingsForm(forms.ModelForm):
    """Bildirim ayarları formu"""
    
    class Meta:
        model = CertificateNotificationSettings
        fields = [
            'name', 'warning_days', 'email_enabled', 'email_recipients',
            'email_template', 'certificate_types', 'environments',
            'criticality_levels', 'check_frequency'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'warning_days': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '[90, 60, 30, 15, 7, 1]'
            }),
            'email_recipients': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '["admin@example.com", "team@example.com"]'
            }),
            'email_template': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10
            }),
            'check_frequency': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class BulkCertificateActionForm(forms.Form):
    """Toplu sertifika işlemleri formu"""
    
    ACTION_CHOICES = [
        ('check_status', 'Durum Kontrol Et'),
        ('create_alert', 'Uyarı Oluştur'),
        ('export', 'Dışa Aktar'),
    ]
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    certificate_ids = forms.CharField(widget=forms.HiddenInput())
