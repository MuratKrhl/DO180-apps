from django import forms
from django.contrib.auth.models import User
from ckeditor.widgets import CKEditorWidget
from .models import Announcement, AnnouncementAttachment, AnnouncementComment

class AnnouncementForm(forms.ModelForm):
    """Gelişmiş duyuru formu"""
    
    class Meta:
        model = Announcement
        fields = [
            'title', 'summary', 'content', 'announcement_type', 'priority', 
            'related_product', 'is_pinned', 'is_urgent', 'start_date', 
            'end_date', 'work_date', 'target_audience'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Duyuru başlığını girin...'
            }),
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Kısa özet (opsiyonel)...'
            }),
            'content': CKEditorWidget(attrs={
                'class': 'form-control'
            }),
            'announcement_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'related_product': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'work_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'target_audience': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Hedef kitle (opsiyonel)...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Tarih alanlarını opsiyonel yap
        self.fields['end_date'].required = False
        self.fields['work_date'].required = False
        self.fields['target_audience'].required = False
        self.fields['summary'].required = False
        
        # Yardım metinleri
        self.fields['is_pinned'].help_text = "Sabitlenmiş duyurular listenin en üstünde görünür"
        self.fields['is_urgent'].help_text = "Acil duyurular özel vurgulanır"
        self.fields['end_date'].help_text = "Boş bırakılırsa süresiz yayında kalır"
        self.fields['work_date'].help_text = "Planlı çalışmalar için çalışma tarihi"
    
    def save(self, commit=True):
        announcement = super().save(commit=False)
        
        if self.user:
            announcement.author = self.user
        
        if commit:
            announcement.save()
        
        return announcement

class AnnouncementFilterForm(forms.Form):
    """Duyuru filtreleme formu"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Başlık veya içerik ara...'
        })
    )
    
    announcement_type = forms.ChoiceField(
        required=False,
        choices=[('', 'Tüm Tipler')] + Announcement.TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        required=False,
        choices=[('', 'Tüm Öncelikler')] + Announcement.PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    related_product = forms.ChoiceField(
        required=False,
        choices=[('', 'Tüm Ürünler')] + Announcement.PRODUCT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Sadece Yayında'), ('all', 'Tümü')] + Announcement.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_range = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Tüm Tarihler'),
            ('today', 'Bugün'),
            ('week', 'Bu Hafta'),
            ('month', 'Bu Ay'),
            ('year', 'Bu Yıl'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class AnnouncementAttachmentForm(forms.ModelForm):
    """Duyuru eki formu"""
    
    class Meta:
        model = AnnouncementAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif'
            })
        }

class AnnouncementCommentForm(forms.ModelForm):
    """Duyuru yorum formu"""
    
    class Meta:
        model = AnnouncementComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Yorumunuzu yazın...'
            })
        }

class BulkAnnouncementActionForm(forms.Form):
    """Toplu duyuru işlem formu"""
    
    ACTION_CHOICES = [
        ('publish', 'Yayınla'),
        ('archive', 'Arşivle'),
        ('delete', 'Sil'),
        ('pin', 'Sabitle'),
        ('unpin', 'Sabitlemeden Çıkar'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    announcement_ids = forms.CharField(widget=forms.HiddenInput())
