from django import forms
from .models import AutomationTask, PlaybookTemplate
from inventory.models import Server, Application

class AutomationTaskForm(forms.ModelForm):
    """Otomasyon görevi formu"""
    
    class Meta:
        model = AutomationTask
        fields = [
            'name', 'description', 'playbook_template', 'target_servers', 
            'target_applications', 'variables', 'priority', 'scheduled_at'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'playbook_template': forms.Select(attrs={'class': 'form-select'}),
            'target_servers': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'target_applications': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5}),
            'variables': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'JSON formatında değişkenler'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target_servers'].queryset = Server.objects.filter(is_active=True)
        self.fields['target_applications'].queryset = Application.objects.filter(is_active=True)
        self.fields['playbook_template'].queryset = PlaybookTemplate.objects.filter(is_active=True)
    
    def clean_variables(self):
        """JSON formatını kontrol et"""
        variables = self.cleaned_data.get('variables')
        if variables:
            try:
                import json
                json.loads(variables)
            except json.JSONDecodeError:
                raise forms.ValidationError('Geçerli JSON formatında olmalıdır.')
        return variables

class PlaybookTemplateForm(forms.ModelForm):
    """Playbook şablonu formu"""
    
    class Meta:
        model = PlaybookTemplate
        fields = [
            'name', 'description', 'category', 'playbook_path', 'inventory_path',
            'required_vars', 'is_dangerous', 'requires_approval', 'allowed_environments'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'playbook_path': forms.TextInput(attrs={'class': 'form-control'}),
            'inventory_path': forms.TextInput(attrs={'class': 'form-control'}),
            'required_vars': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'allowed_environments': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
