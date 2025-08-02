from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from core.models import BaseModel
from ckeditor.fields import RichTextField

class Announcement(BaseModel):
    """Duyuru modeli - Geliştirilmiş versiyon"""
    
    TYPE_CHOICES = [
        ('info', 'Bilgi'),
        ('warning', 'Uyarı'),
        ('success', 'Başarı'),
        ('danger', 'Tehlike'),
        ('maintenance', 'Bakım'),
        ('planned_work', 'Planlı Çalışma'),
        ('outage', 'Kesinti'),
        ('update', 'Güncelleme'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Taslak'),
        ('published', 'Yayında'),
        ('archived', 'Arşivlenmiş'),
        ('scheduled', 'Zamanlanmış'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Düşük'),
        ('normal', 'Normal'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik'),
    ]
    
    PRODUCT_CHOICES = [
        ('general', 'Genel'),
        ('middleware', 'Middleware'),
        ('database', 'Veritabanı'),
        ('network', 'Ağ'),
        ('security', 'Güvenlik'),
        ('application', 'Uygulama'),
        ('infrastructure', 'Altyapı'),
    ]
    
    # Temel Bilgiler
    title = models.CharField(max_length=200, verbose_name="Başlık")
    content = RichTextField(verbose_name="İçerik", help_text="Zengin metin editörü ile içerik oluşturun")
    summary = models.TextField(max_length=500, verbose_name="Özet", blank=True, help_text="Kısa özet (liste görünümünde gösterilir)")
    
    # Kategorizasyon
    announcement_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info', verbose_name="Duyuru Tipi")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal', verbose_name="Öncelik Seviyesi")
    related_product = models.CharField(max_length=20, choices=PRODUCT_CHOICES, default='general', verbose_name="İlgili Ürün")
    
    # Durum Yönetimi
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Durum")
    is_pinned = models.BooleanField(default=False, verbose_name="Sabitlenmiş")
    is_urgent = models.BooleanField(default=False, verbose_name="Acil")
    
    # Tarih Yönetimi
    start_date = models.DateTimeField(verbose_name="Başlangıç Tarihi", default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True, verbose_name="Bitiş Tarihi")
    work_date = models.DateTimeField(null=True, blank=True, verbose_name="Çalışma Tarihi", help_text="Planlı çalışmalar için")
    
    # Hedefleme
    target_audience = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Hedef Kitle",
        help_text="Boş bırakılırsa herkese gösterilir"
    )
    
    # İstatistikler
    view_count = models.PositiveIntegerField(default=0, verbose_name="Görüntülenme Sayısı")
    
    # Yazar Bilgisi
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Yazar", related_name='announcements')
    
    class Meta:
        verbose_name = "Duyuru"
        verbose_name_plural = "Duyurular"
        ordering = ['-is_pinned', '-priority', '-start_date']
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['is_pinned', 'priority']),
            models.Index(fields=['announcement_type', 'related_product']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def get_absolute_url(self):
        return reverse('announcements:announcement_detail', kwargs={'pk': self.pk})

    @property
    def is_active_now(self):
        """Duyurunun şu anda aktif olup olmadığını kontrol et"""
        now = timezone.now()
        
        if self.status != 'published':
            return False
            
        if not self.is_active:
            return False
            
        if self.start_date > now:
            return False
            
        if self.end_date and self.end_date < now:
            return False
            
        return True

    @property
    def is_scheduled(self):
        """Zamanlanmış mı?"""
        return self.status == 'scheduled' or (self.start_date > timezone.now())

    @property
    def is_expired(self):
        """Süresi dolmuş mu?"""
        return self.end_date and self.end_date < timezone.now()

    @property
    def type_icon(self):
        """Duyuru tipine göre ikon döndür"""
        icons = {
            'info': 'ri-information-line',
            'warning': 'ri-alert-line',
            'success': 'ri-checkbox-circle-line',
            'danger': 'ri-error-warning-line',
            'maintenance': 'ri-tools-line',
            'planned_work': 'ri-calendar-event-line',
            'outage': 'ri-shut-down-line',
            'update': 'ri-refresh-line',
        }
        return icons.get(self.announcement_type, 'ri-notification-3-line')

    @property
    def type_class(self):
        """Duyuru tipine göre CSS sınıfı döndür"""
        classes = {
            'info': 'alert-info',
            'warning': 'alert-warning',
            'success': 'alert-success',
            'danger': 'alert-danger',
            'maintenance': 'alert-secondary',
            'planned_work': 'alert-primary',
            'outage': 'alert-danger',
            'update': 'alert-info',
        }
        return classes.get(self.announcement_type, 'alert-info')

    @property
    def priority_class(self):
        """Öncelik seviyesine göre CSS sınıfı"""
        classes = {
            'low': 'text-muted',
            'normal': 'text-info',
            'high': 'text-warning',
            'critical': 'text-danger',
        }
        return classes.get(self.priority, 'text-info')

    @property
    def status_badge_class(self):
        """Durum badge sınıfı"""
        classes = {
            'draft': 'bg-secondary',
            'published': 'bg-success',
            'archived': 'bg-dark',
            'scheduled': 'bg-primary',
        }
        return classes.get(self.status, 'bg-secondary')

    def increment_view_count(self):
        """Görüntülenme sayısını artır"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

    def publish(self):
        """Duyuruyu yayınla"""
        self.status = 'published'
        if not self.start_date:
            self.start_date = timezone.now()
        self.save(update_fields=['status', 'start_date'])

    def archive(self):
        """Duyuruyu arşivle"""
        self.status = 'archived'
        self.save(update_fields=['status'])

    def schedule(self, start_date):
        """Duyuruyu zamanla"""
        self.status = 'scheduled'
        self.start_date = start_date
        self.save(update_fields=['status', 'start_date'])

class AnnouncementAttachment(BaseModel):
    """Duyuru ekleri"""
    
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='attachments', verbose_name="Duyuru")
    file = models.FileField(upload_to='announcements/attachments/', verbose_name="Dosya")
    original_name = models.CharField(max_length=255, verbose_name="Orijinal Dosya Adı")
    file_size = models.PositiveIntegerField(verbose_name="Dosya Boyutu (bytes)")
    content_type = models.CharField(max_length=100, verbose_name="İçerik Tipi")
    
    class Meta:
        verbose_name = "Duyuru Eki"
        verbose_name_plural = "Duyuru Ekleri"
    
    def __str__(self):
        return f"{self.announcement.title} - {self.original_name}"

class AnnouncementView(models.Model):
    """Duyuru görüntüleme takibi"""
    
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Duyuru Görüntüleme"
        verbose_name_plural = "Duyuru Görüntülemeler"
        unique_together = ['announcement', 'user', 'ip_address']

class AnnouncementComment(BaseModel):
    """Duyuru yorumları"""
    
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='comments', verbose_name="Duyuru")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    content = models.TextField(verbose_name="Yorum İçeriği")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', verbose_name="Üst Yorum")
    
    class Meta:
        verbose_name = "Duyuru Yorumu"
        verbose_name_plural = "Duyuru Yorumları"
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.announcement.title}"

class AnnouncementSubscription(BaseModel):
    """Duyuru abonelikleri"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    announcement_types = models.JSONField(default=list, verbose_name="Duyuru Tipleri")
    products = models.JSONField(default=list, verbose_name="Ürünler")
    priorities = models.JSONField(default=list, verbose_name="Öncelik Seviyeleri")
    email_notifications = models.BooleanField(default=True, verbose_name="E-posta Bildirimleri")
    
    class Meta:
        verbose_name = "Duyuru Aboneliği"
        verbose_name_plural = "Duyuru Abonelikleri"
        unique_together = ['user']
    
    def __str__(self):
        return f"{self.user.username} - Abonelik"
