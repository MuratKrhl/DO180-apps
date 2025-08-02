from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.generic import ListView, DetailView, RedirectView
from django.http import JsonResponse
from django.urls import reverse
from .models import Question, Category, Document, DocumentAccess
from .forms import QuestionForm, CategoryForm
from .services import DocumentAnalyticsService
import logging

logger = logging.getLogger(__name__)

# ============ Doküman Views ============

class CategoryDocumentListView(LoginRequiredMixin, ListView):
    """Kategori bazlı doküman listesi"""
    model = Document
    template_name = 'askgt/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20

    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        queryset = Document.objects.filter(is_active=True).select_related('category')
        
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filtreleme
        search = self.request.GET.get('search')
        document_type = self.request.GET.get('type')
        source_type = self.request.GET.get('source')
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(summary__icontains=search) |
                Q(content_preview__icontains=search) |
                Q(tags__icontains=search)
            )
        
        if document_type:
            queryset = queryset.filter(document_type=document_type)
        
        if source_type:
            queryset = queryset.filter(source_type=source_type)
        
        # Sıralama
        order_by = self.request.GET.get('order_by', '-created_at')
        if order_by in ['-created_at', '-view_count', 'title', '-last_modified']:
            queryset = queryset.order_by(order_by)
        
        return queryset.order_by('-is_featured', order_by)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_slug = self.kwargs.get('category_slug')
        
        if category_slug:
            context['current_category'] = get_object_or_404(Category, slug=category_slug, is_active=True)
        else:
            context['current_category'] = None
        
        # Filtreleme seçenekleri
        context['document_types'] = Document.DOCUMENT_TYPES
        context['source_types'] = Document.SOURCE_TYPES
        
        # Mevcut filtreler
        context['current_search'] = self.request.GET.get('search', '')
        context['current_type'] = self.request.GET.get('type', '')
        context['current_source'] = self.request.GET.get('source', '')
        context['current_order'] = self.request.GET.get('order_by', '-created_at')
        
        # İstatistikler
        context['total_documents'] = self.get_queryset().count()
        context['featured_documents'] = Document.objects.filter(
            is_active=True, 
            is_featured=True
        ).select_related('category')[:5]
        
        return context

class DocumentRedirectView(LoginRequiredMixin, RedirectView):
    """Doküman erişim loglaması ve yönlendirme"""
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        document = get_object_or_404(Document, pk=kwargs['pk'], is_active=True)
        
        # Erişimi logla
        DocumentAnalyticsService.log_document_access(document, self.request.user, self.request)
        
        return document.original_url

class AllDocumentsListView(LoginRequiredMixin, ListView):
    """Tüm dokümanlar listesi"""
    model = Document
    template_name = 'askgt/all_documents.html'
    context_object_name = 'documents'
    paginate_by = 25

    def get_queryset(self):
        queryset = Document.objects.filter(is_active=True).select_related('category')
        
        # Arama
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(summary__icontains=search) |
                Q(tags__icontains=search)
            )
        
        return queryset.order_by('-is_featured', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Kategori istatistikleri
        context['category_stats'] = DocumentAnalyticsService.get_category_stats()
        context['popular_documents'] = DocumentAnalyticsService.get_popular_documents(10)
        context['recent_documents'] = DocumentAnalyticsService.get_recent_documents(10)
        
        return context

# ============ Soru-Cevap Views (Mevcut) ============

@login_required
def question_list(request):
    """Soru listesi"""
    questions = Question.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(is_active=True)
    
    # Filtreleme
    search = request.GET.get('search')
    category_id = request.GET.get('category')
    priority = request.GET.get('priority')
    featured = request.GET.get('featured')
    
    if search:
        questions = questions.filter(
            Q(title__icontains=search) |
            Q(question__icontains=search) |
            Q(answer__icontains=search) |
            Q(tags__icontains=search)
        )
    
    if category_id:
        questions = questions.filter(category_id=category_id)
    
    if priority:
        questions = questions.filter(priority=priority)
    
    if featured:
        questions = questions.filter(is_featured=True)
    
    # Sayfalama
    paginator = Paginator(questions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search': search,
        'category_id': int(category_id) if category_id else None,
        'priority': priority,
        'featured': featured,
        'priority_choices': Question.PRIORITY_CHOICES,
        'featured_questions': Question.objects.filter(is_active=True, is_featured=True)[:5],
    }
    return render(request, 'askgt/question_list.html', context)

@login_required
def question_detail(request, pk):
    """Soru detayı"""
    question = get_object_or_404(Question, pk=pk, is_active=True)
    question.increment_view_count()
    
    # İlgili sorular
    related_questions = Question.objects.filter(
        category=question.category,
        is_active=True
    ).exclude(pk=question.pk)[:5]
    
    context = {
        'question': question,
        'related_questions': related_questions,
    }
    return render(request, 'askgt/question_detail.html', context)

@login_required
def category_list(request):
    """Kategori listesi"""
    categories = Category.objects.filter(is_active=True).prefetch_related('questions', 'documents')
    
    # Her kategori için istatistikler
    for category in categories:
        category.question_count = category.questions.filter(is_active=True).count()
        category.document_count = category.documents.filter(is_active=True).count()
        category.total_count = category.question_count + category.document_count
    
    context = {
        'categories': categories,
    }
    return render(request, 'askgt/category_list.html', context)

# ============ API Views ============

@login_required
def document_search_api(request):
    """Doküman arama API"""
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    limit = int(request.GET.get('limit', 10))
    
    documents = Document.objects.filter(is_active=True)
    
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(summary__icontains=query) |
            Q(tags__icontains=query)
        )
    
    if category_slug:
        documents = documents.filter(category__slug=category_slug)
    
    documents = documents.select_related('category')[:limit]
    
    results = []
    for doc in documents:
        results.append({
            'id': doc.id,
            'title': doc.title,
            'summary': doc.get_display_summary(),
            'url': doc.get_absolute_url(),
            'category': {
                'name': doc.category.name,
                'slug': doc.category.slug,
                'icon': doc.category.icon
            },
            'document_type': doc.get_document_type_display(),
            'view_count': doc.view_count,
            'is_featured': doc.is_featured
        })
    
    return JsonResponse({
        'results': results,
        'total': len(results)
    })

# ============ Yönetim Paneli Views ============

@login_required
@permission_required('askgt.view_question')
def manage_dashboard(request):
    """AskGT yönetim dashboard"""
    # İstatistikler
    stats = {
        'total_questions': Question.objects.filter(is_active=True).count(),
        'total_documents': Document.objects.filter(is_active=True).count(),
        'total_categories': Category.objects.filter(is_active=True).count(),
        'featured_questions': Question.objects.filter(is_active=True, is_featured=True).count(),
        'featured_documents': Document.objects.filter(is_active=True, is_featured=True).count(),
        'recent_questions': Question.objects.filter(is_active=True).order_by('-created_at')[:5],
        'recent_documents': Document.objects.filter(is_active=True).order_by('-created_at')[:5],
    }
    
    # Kategori bazında istatistikler
    category_stats = Category.objects.filter(is_active=True).annotate(
        question_count=Count('questions', filter=Q(questions__is_active=True)),
        document_count=Count('documents', filter=Q(documents__is_active=True))
    ).order_by('-question_count', '-document_count')
    
    # Popüler dokümanlar
    popular_documents = DocumentAnalyticsService.get_popular_documents(10)
    
    context = {
        'stats': stats,
        'category_stats': category_stats,
        'popular_documents': popular_documents,
    }
    return render(request, 'askgt/manage_dashboard.html', context)

# Diğer yönetim view'ları (question_create, question_edit, vb.) mevcut kodda var
@login_required
@permission_required('askgt.add_question')
def question_create(request):
    """Yeni soru oluştur"""
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.created_by = request.user
            question.save()
            
            messages.success(request, f'Soru "{question.title}" başarıyla oluşturuldu.')
            return redirect('askgt:question_detail', pk=question.pk)
    else:
        form = QuestionForm()
    
    context = {
        'form': form,
        'title': 'Yeni Soru Ekle',
    }
    return render(request, 'askgt/question_form.html', context)

@login_required
@permission_required('askgt.change_question')
def question_edit(request, pk):
    """Soru düzenle"""
    question = get_object_or_404(Question, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            messages.success(request, f'Soru "{question.title}" başarıyla güncellendi.')
            return redirect('askgt:question_detail', pk=question.pk)
    else:
        form = QuestionForm(instance=question)
    
    context = {
        'form': form,
        'question': question,
        'title': 'Soru Düzenle',
    }
    return render(request, 'askgt/question_form.html', context)

@login_required
@permission_required('askgt.delete_question')
def question_delete(request, pk):
    """Soru sil"""
    question = get_object_or_404(Question, pk=pk, is_active=True)
    
    if request.method == 'POST':
        question.is_active = False
        question.save()
        messages.success(request, f'Soru "{question.title}" başarıyla silindi.')
        return redirect('askgt:manage_dashboard')
    
    context = {
        'question': question,
    }
    return render(request, 'askgt/question_confirm_delete.html', context)

@login_required
@permission_required('askgt.add_category')
def category_create(request):
    """Yeni kategori oluştur"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            
            messages.success(request, f'Kategori "{category.name}" başarıyla oluşturuldu.')
            return redirect('askgt:category_list')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'title': 'Yeni Kategori Ekle',
    }
    return render(request, 'askgt/category_form.html', context)

@login_required
@permission_required('askgt.change_category')
def category_edit(request, pk):
    """Kategori düzenle"""
    category = get_object_or_404(Category, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Kategori "{category.name}" başarıyla güncellendi.')
            return redirect('askgt:category_list')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': 'Kategori Düzenle',
    }
    return render(request, 'askgt/category_form.html', context)

@login_required
@permission_required('askgt.delete_category')
def category_delete(request, pk):
    """Kategori sil"""
    category = get_object_or_404(Category, pk=pk, is_active=True)
    
    if request.method == 'POST':
        category.is_active = False
        category.save()
        messages.success(request, f'Kategori "{category.name}" başarıyla silindi.')
        return redirect('askgt:category_list')
    
    context = {
        'category': category,
    }
    return render(request, 'askgt/category_confirm_delete.html', context)
