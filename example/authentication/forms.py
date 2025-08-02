from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

class CustomLoginForm(forms.Form):
    """Özel login formu"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kullanıcı Adı',
            'autofocus': True,
        }),
        label='Kullanıcı Adı'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Şifre',
        }),
        label='Şifre'
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='Beni Hatırla'
    )

class UserProfileForm(forms.ModelForm):
    """Kullanıcı profil formu"""
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Ad'
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='Soyad'
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        label='E-posta'
    )
    
    class Meta:
        from .models import UserProfile
        model = UserProfile
        fields = ['department', 'phone', 'preferred_language', 'timezone']
        widgets = {
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'preferred_language': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            
            if commit:
                self.user.save()
                profile.save()
        
        return profile
