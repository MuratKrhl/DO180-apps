from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from datetime import timedelta, datetime
from .models import Announcement, AnnouncementAttachment, AnnouncementComment, AnnouncementView
from .forms import AnnouncementForm, AnnouncementFilterForm, AnnouncementAttachmentForm, AnnouncementCommentForm, BulkAnnouncementActionForm

class AnnouncementListView(LoginRequiredMixin, ListView):
    """Gelişmiş duyuru listesi"""
    model = Announcement
    template_name = 'announcements/announcement_list.html'
    context_object_name = 'announcements'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = Announcement.objects.select_related('author').prefetch_related('attachments')
        
        # Kullanıcı yetkisine göre filtreleme
        if not self.request.user.has_perm('announcements.view_all_announcements'):
            queryset = queryset.filter(status='published', is_active=True)
            
            # Aktif duyuruları filtrele
            now = timezone.now()
            queryset = queryset.filter(
                start_date__lte=now
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=now)
            )
        
        # Filtreleme
        form = AnnouncementFilterForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            announcement_type = form.cleaned_data.get('announcement_type')
            priority = form.cleaned_data.get('priority')
            related_product = form.cleaned_data.get('related_product')
            status = form.cleaned_data.get('status')
            date_range = form.cleaned_data.get('date_range')
            
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(content__icontains=search) |
                    Q(summary__icontains=search)
                )
            
            if announcement_type:
                queryset = queryset.filter(announcement_type=announcement_type)
            
            if priority:
                queryset = queryset.filter(priority=priority)
            
            if related_product:
                queryset = queryset.filter(related_product=related_product)
            
            if status and status != 'all':
                queryset = queryset.filter(status=status)
            
            if date_range:
                now = timezone.now()
                if date_range == 'today':
                    queryset = queryset.filter(start_date__date=now.date())
                elif date_range == 'week':
                    week_start = now - timedelta(days=now.weekday())
                    queryset = queryset.filter(start_date__gte=week_start)
                elif date_range == 'month':
                    queryset = queryset.filter(start_date__month=now.month, start_date__year=now.year)
                elif date_range == 'year':
                    queryset = queryset.filter(start_date__year=now.year)
        
        return queryset.order_by('-is_pinned', '-priority', '-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtreleme formu
        context['filter_form'] = AnnouncementFilterForm(self.request.GET)
        
        # İstatistikler
        context['stats'] = {
            'total': Announcement.objects.filter(is_active=True).count(),
            'published': Announcement.objects.filter(status='published', is_active=True).count(),
            'draft': Announcement.objects.filter(status='draft', is_active=True).count(),
            'urgent': Announcement.objects.filter(is_urgent=True, status='published', is_active=True).count(),
        }
        
        # Acil duyurular
        context['urgent_announcements'] = Announcement.objects.filter(
            is_active=True,
            is_urgent=True,
            status='published',
            start_date__lte=timezone.now()
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=timezone.now())
        )[:3]
        
        # Sabitlenmiş duyurular
        context['pinned_announcements'] = Announcement.objects.filter(
            is_active=True,
            is_pinned=True,
            status='published',
            start_date__lte=timezone.now()
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=timezone.now())
        )[:5]
        
        return context

class AnnouncementDetailView(LoginRequiredMixin, DetailView):
    """Duyuru detay görünümü"""
    model = Announcement
    template_name = 'announcements/announcement_detail.html'
    context_object_name = 'announcement'
    
    def get_queryset(self):
        queryset = Announcement.objects.select_related('author').prefetch_related(
            'attachments', 'comments__user', 'comments__replies__user'
        )
        
        # Kullanıcı yetkisine göre filtreleme
        if not self.request.user.has_perm('announcements.view_all_announcements'):
            queryset = queryset.filter(status='published', is_active=True)
        
        return queryset
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Görüntülenme sayısını artır
        obj.increment_view_count()
        
        # Görüntülenme kaydı oluştur
        AnnouncementView.objects.get_or_create(
            announcement=obj,
            user=self.request.user if self.request.user.is_authenticated else None,
            ip_address=self.get_client_ip(),
            defaults={
                'user_agent': self.request.META.get('HTTP_USER_AGENT', '')[:500]
            }
        )
        
        return obj
    
    def get_client_ip(self):
        """İstemci IP adresini al"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Yorum formu
        context['comment_form'] = AnnouncementCommentForm()
        
        # İlgili duyurular
        context['related_announcements'] = Announcement.objects.filter(
            is_active=True,
            status='published',
            announcement_type=self.object.announcement_type
        ).exclude(pk=self.object.pk)[:5]
        
        # Son duyurular
        context['recent_announcements'] = Announcement.objects.filter(
            is_active=True,
            status='published',
            start_date__lte=timezone.now()
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=timezone.now())
        ).exclude(pk=self.object.pk)[:5]
        
        return context

class AnnouncementCreateView(PermissionRequiredMixin, CreateView):
    """Duyuru oluşturma"""
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'announcements/announcement_form.html'
    permission_required = 'announcements.add_announcement'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Kaydetme tipini kontrol et
        save_type = self.request.POST.get('save_type', 'draft')
        
        if save_type == 'publish':
            form.instance.status = 'published'
            if not form.instance.start_date:
                form.instance.start_date = timezone.now()
            messages.success(self.request, f'Duyuru "{form.instance.title}" başarıyla yayınlandı.')
        elif save_type == 'schedule':
            form.instance.status = 'scheduled'
            messages.success(self.request, f'Duyuru "{form.instance.title}" zamanlandı.')
        else:
            form.instance.status = 'draft'
            messages.success(self.request, f'Duyuru "{form.instance.title}" taslak olarak kaydedildi.')
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('announcements:announcement_detail', kwargs={'pk': self.object.pk})

class AnnouncementUpdateView(PermissionRequiredMixin, UpdateView):
    """Duyuru güncelleme"""
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'announcements/announcement_form.html'
    permission_required = 'announcements.change_announcement'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Kaydetme tipini kontrol et
        save_type = self.request.POST.get('save_type', 'update')
        
        if save_type == 'publish':
            form.instance.status = 'published'
            if not form.instance.start_date:
                form.instance.start_date = timezone.now()
            messages.success(self.request, f'Duyuru "{form.instance.title}" başarıyla yayınlandı.')
        elif save_type == 'archive':
            form.instance.status = 'archived'
            messages.success(self.request, f'Duyuru "{form.instance.title}" arşivlendi.')
        else:
            messages.success(self.request, f'Duyuru "{form.instance.title}" güncellendi.')
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('announcements:announcement_detail', kwargs={'pk': self.object.pk})

class AnnouncementDeleteView(PermissionRequiredMixin, DeleteView):
    """Duyuru silme"""
    model = Announcement
    template_name = 'announcements/announcement_confirm_delete.html'
    permission_required = 'announcements.delete_announcement'
    success_url = reverse_lazy('announcements:announcement_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Soft delete
        self.object.is_active = False
        self.object.save()
        messages.success(request, f'Duyuru "{self.object.title}" başarıyla silindi.')
        return HttpResponseRedirect(self.get_success_url())

@login_required
@permission_required('announcements.add_announcement')
def announcement_quick_create(request):
    """Hızlı duyuru oluşturma (AJAX)"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, user=request.user)
        if form.is_valid():
            announcement = form.save()
            
            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Duyuru başarıyla oluşturuldu.',
                    'announcement_id': announcement.id,
                    'announcement_url': announcement.get_absolute_url()
                })
            
            return redirect('announcements:announcement_detail', pk=announcement.pk)
    else:
        form = AnnouncementForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Hızlı Duyuru Oluştur',
        'is_modal': True
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('announcements/announcement_quick_form.html', context, request)
        return JsonResponse({'html': html})
    
    return render(request, 'announcements/announcement_form.html', context)

@login_required
@permission_required('announcements.change_announcement')
def announcement_bulk_action(request):
    """Toplu duyuru işlemleri"""
    if request.method == 'POST':
        form = BulkAnnouncementActionForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            announcement_ids = form.cleaned_data['announcement_ids'].split(',')
            
            announcements = Announcement.objects.filter(
                id__in=announcement_ids,
                is_active=True
            )
            
            count = 0
            for announcement in announcements:
                if action == 'publish':
                    announcement.publish()
                    count += 1
                elif action == 'archive':
                    announcement.archive()
                    count += 1
                elif action == 'delete':
                    announcement.is_active = False
                    announcement.save()
                    count += 1
                elif action == 'pin':
                    announcement.is_pinned = True
                    announcement.save()
                    count += 1
                elif action == 'unpin':
                    announcement.is_pinned = False
                    announcement.save()
                    count += 1
            
            messages.success(request, f'{count} duyuru için {action} işlemi tamamlandı.')
    
    return redirect('announcements:announcement_list')

@login_required
def announcement_comment_create(request, pk):
    """Duyuru yorumu oluştur"""
    announcement = get_object_or_404(Announcement, pk=pk, is_active=True)
    
    if request.method == 'POST':
        form = AnnouncementCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.announcement = announcement
            comment.user = request.user
            
            # Üst yorum kontrolü
            parent_id = request.POST.get('parent_id')
            if parent_id:
                comment.parent = get_object_or_404(AnnouncementComment, pk=parent_id)
            
            comment.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Yorum başarıyla eklendi.',
                    'comment_html': render_to_string(
                        'announcements/comment_item.html',
                        {'comment': comment},
                        request
                    )
                })
            
            messages.success(request, 'Yorumunuz başarıyla eklendi.')
    
    return redirect('announcements:announcement_detail', pk=pk)

@login_required
@permission_required('announcements.view_announcement_stats')
def announcement_dashboard(request):
    """Duyuru yönetim dashboard'u"""
    # İstatistikler
    stats = {
        'total': Announcement.objects.filter(is_active=True).count(),
        'published': Announcement.objects.filter(status='published', is_active=True).count(),
        'draft': Announcement.objects.filter(status='draft', is_active=True).count(),
        'scheduled': Announcement.objects.filter(status='scheduled', is_active=True).count(),
        'archived': Announcement.objects.filter(status='archived', is_active=True).count(),
    }
    
    # Kullanıcının duyuruları
    user_announcements = Announcement.objects.filter(
        author=request.user,
        is_active=True
    ).order_by('-created_at')[:10]
    
    # Son görüntülenen duyurular
    recent_views = AnnouncementView.objects.filter(
        user=request.user
    ).select_related('announcement').order_by('-viewed_at')[:10]
    
    # Popüler duyurular
    popular_announcements = Announcement.objects.filter(
        is_active=True,
        status='published'
    ).order_by('-view_count')[:10]
    
    # Aylık istatistikler
    now = timezone.now()
    monthly_stats = []
    for i in range(6):
        month_start = now.replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end - timedelta(days=month_end.day)
        
        count = Announcement.objects.filter(
            created_at__gte=month_start,
            created_at__lte=month_end,
            is_active=True
        ).count()
        
        monthly_stats.append({
            'month': month_start.strftime('%B %Y'),
            'count': count
        })
    
    context = {
        'stats': stats,
        'user_announcements': user_announcements,
        'recent_views': recent_views,
        'popular_announcements': popular_announcements,
        'monthly_stats': list(reversed(monthly_stats)),
    }
    
    return render(request, 'announcements/announcement_dashboard.html', context)

# API Views for AJAX
@login_required
def announcement_api_list(request):
    """Duyuru listesi API (AJAX için)"""
    announcements = Announcement.objects.filter(
        is_active=True,
        status='published',
        start_date__lte=timezone.now()
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=timezone.now())
    ).order_by('-is_pinned', '-priority', '-start_date')[:10]
    
    data = []
    for announcement in announcements:
        data.append({
            'id': announcement.id,
            'title': announcement.title,
            'summary': announcement.summary or announcement.content[:100],
            'type': announcement.announcement_type,
            'type_display': announcement.get_announcement_type_display(),
            'priority': announcement.priority,
            'is_urgent': announcement.is_urgent,
            'is_pinned': announcement.is_pinned,
            'start_date': announcement.start_date.isoformat(),
            'url': announcement.get_absolute_url(),
            'type_icon': announcement.type_icon,
            'type_class': announcement.type_class,
        })
    
    return JsonResponse({'announcements': data})
