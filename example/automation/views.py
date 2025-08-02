from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from .models import AutomationTask, PlaybookTemplate, TaskExecution
from .services import AnsibleService
from .forms import AutomationTaskForm, PlaybookTemplateForm
import json

@login_required
def automation_list(request):
    """Otomasyon görev listesi"""
    tasks = AutomationTask.objects.filter(is_active=True).select_related(
        'playbook_template', 'created_by', 'approved_by'
    )
    
    # Filtreleme
    search = request.GET.get('search')
    status = request.GET.get('status')
    category = request.GET.get('category')
    priority = request.GET.get('priority')
    
    if search:
        tasks = tasks.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(playbook_template__name__icontains=search)
        )
    
    if status:
        tasks = tasks.filter(status=status)
    
    if category:
        tasks = tasks.filter(playbook_template__category=category)
    
    if priority:
        tasks = tasks.filter(priority=priority)
    
    # Sayfalama
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # İstatistikler
    stats = {
        'total': AutomationTask.objects.filter(is_active=True).count(),
        'pending': AutomationTask.objects.filter(is_active=True, status='pending').count(),
        'running': AutomationTask.objects.filter(is_active=True, status='running').count(),
        'completed': AutomationTask.objects.filter(is_active=True, status='completed').count(),
        'failed': AutomationTask.objects.filter(is_active=True, status='failed').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'category': category,
        'priority': priority,
        'status_choices': AutomationTask.STATUS_CHOICES,
        'category_choices': PlaybookTemplate.CATEGORY_CHOICES,
        'priority_choices': AutomationTask.PRIORITY_CHOICES,
        'stats': stats,
    }
    return render(request, 'automation/automation_list.html', context)

@login_required
@permission_required('automation.add_automationtask')
def task_create(request):
    """Yeni otomasyon görevi oluştur"""
    if request.method == 'POST':
        form = AutomationTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            form.save_m2m()  # ManyToMany alanları için
            
            messages.success(request, f'Otomasyon görevi "{task.name}" başarıyla oluşturuldu.')
            return redirect('automation:task_detail', pk=task.pk)
    else:
        form = AutomationTaskForm()
    
    context = {
        'form': form,
        'title': 'Yeni Otomasyon Görevi',
    }
    return render(request, 'automation/task_form.html', context)

@login_required
def task_detail(request, pk):
    """Otomasyon görevi detayı"""
    task = get_object_or_404(AutomationTask, pk=pk, is_active=True)
    executions = task.executions.all()[:10]  # Son 10 çalıştırma
    
    context = {
        'task': task,
        'executions': executions,
        'can_execute': task.can_be_executed and request.user.has_perm('automation.execute_automationtask'),
        'can_approve': (task.playbook_template.requires_approval and 
                       task.status == 'pending' and 
                       request.user.has_perm('automation.approve_automationtask')),
    }
    return render(request, 'automation/task_detail.html', context)

@login_required
@permission_required('automation.execute_automationtask')
def task_execute(request, pk):
    """Görevi çalıştır"""
    task = get_object_or_404(AutomationTask, pk=pk, is_active=True)
    
    if not task.can_be_executed:
        messages.error(request, 'Bu görev çalıştırılamaz.')
        return redirect('automation:task_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            service = AnsibleService()
            execution = service.execute_task(task.id)
            
            if execution.is_successful:
                messages.success(request, 'Görev başarıyla çalıştırıldı.')
            else:
                messages.error(request, 'Görev çalıştırıldı ancak hata oluştu.')
                
        except Exception as e:
            messages.error(request, f'Görev çalıştırma hatası: {str(e)}')
    
    return redirect('automation:task_detail', pk=pk)

@login_required
@permission_required('automation.approve_automationtask')
def task_approve(request, pk):
    """Görevi onayla"""
    task = get_object_or_404(AutomationTask, pk=pk, is_active=True)
    
    if task.status == 'pending' and task.playbook_template.requires_approval:
        task.status = 'approved'
        task.approved_by = request.user
        task.approved_at = timezone.now()
        task.save()
        
        messages.success(request, f'Görev "{task.name}" onaylandı.')
    else:
        messages.error(request, 'Bu görev onaylanamaz.')
    
    return redirect('automation:task_detail', pk=pk)

@login_required
def playbook_list(request):
    """Playbook şablonları listesi"""
    templates = PlaybookTemplate.objects.filter(is_active=True)
    
    # Filtreleme
    search = request.GET.get('search')
    category = request.GET.get('category')
    
    if search:
        templates = templates.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    if category:
        templates = templates.filter(category=category)
    
    context = {
        'templates': templates,
        'search': search,
        'category': category,
        'category_choices': PlaybookTemplate.CATEGORY_CHOICES,
    }
    return render(request, 'automation/playbook_list.html', context)

@login_required
def execution_detail(request, pk):
    """Çalıştırma detayı"""
    execution = get_object_or_404(TaskExecution, pk=pk)
    
    context = {
        'execution': execution,
    }
    return render(request, 'automation/execution_detail.html', context)

# API Views
@login_required
def task_status_api(request, pk):
    """Görev durumu API"""
    task = get_object_or_404(AutomationTask, pk=pk)
    
    data = {
        'status': task.status,
        'status_display': task.get_status_display(),
        'status_color': task.status_color,
        'started_at': task.started_at.isoformat() if task.started_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
    }
    
    return JsonResponse(data)
