from django import forms
from .models import Question, Category

class QuestionForm(forms.ModelForm):
    """Soru formu"""
    
    class Meta:
        model = Question
        fields = [
            'title', 'question', 'answer', 'category', 'tags', 
            'priority', 'is_featured'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Etiketleri virgülle ayırın'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }

class CategoryForm(forms.ModelForm):
    """Kategori formu"""
    
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'icon', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ri-question-line'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
