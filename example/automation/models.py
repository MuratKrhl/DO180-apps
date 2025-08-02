from django.db import models
from django.contrib.auth.models import User
from core.models import BaseModel
from inventory.models import Server, Application
import json

class PlaybookTemplate(BaseModel):
    """Ansible Playbook şablonları"""
    CATEGORY_CHOICES = [
        ('server', 'Sunucu İşlemleri'),
        ('application', 'Uygulama İşlemleri'),
        ('maintenance', 'Bakım İşlemleri'),
        ('monitoring', 'İzleme İşlemleri'),
        ('security', 'Güvenlik İşlemleri'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Playbook Adı")
    description = models.TextField(verbose_name="Açıklama")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name="Kategori")
    playbook_path = models.CharField(max_length=500, verbose_name="Playbook Dosya Yolu")
    inventory_path = models.CharField(max_length=500, blank=True, verbose_name="Inventory Dosya Yolu")
    required_vars = models.JSONField(default=dict, verbose_name="Gerekli Değişkenler", help_text="JSON formatında")
    is_dangerous = models.BooleanField(default=False, verbose_name="Tehlikeli İşlem")
    requires_approval = models.BooleanField(default=False, verbose_name="Onay Gerektirir")
    allowed_environments = models.JSONField(default=list, verbose_name="İzin Verilen Ortamlar")
    
    class Meta:
        verbose_name = "Playbook Şablonu"
        verbose_name_plural = "Playbook Şablonları"
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    def get_required_vars_list(self):
        """Gerekli değişkenleri liste olarak döndür"""
        if isinstance(self.required_vars, dict):
            return list(self.required_vars.keys())
        return []

class AutomationTask(BaseModel):
    """Otomasyon görevleri"""
    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('approved', 'Onaylandı'),
        ('running', 'Çalışıyor'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('cancelled', 'İptal Edildi'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Görev Adı")
    description = models.TextField(verbose_name="Açıklama")
    playbook_template = models.ForeignKey(PlaybookTemplate, on_delete=models.CASCADE, verbose_name="Playbook Şablonu")
    target_servers = models.ManyToManyField(Server, blank=True, verbose_name="Hedef Sunucular")
    target_applications = models.ManyToManyField(Application, blank=True, verbose_name="Hedef Uygulamalar")
    variables = models.JSONField(default=dict, verbose_name="Değişkenler")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Durum")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="Öncelik")
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name="Zamanlanmış Tarih")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Başlangıç Tarihi")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tamamlanma Tarihi")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_tasks', verbose_name="Onaylayan")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Onay Tarihi")
    
    class Meta:
        verbose_name = "Otomasyon Görevi"
        verbose_name_plural = "Otomasyon Görevleri"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.get_status_display()}"

    @property
    def can_be_executed(self):
        """Görevin çalıştırılabilir olup olmadığını kontrol et"""
        if self.playbook_template.requires_approval and self.status != 'approved':
            return False
        return self.status in ['pending', 'approved']

    @property
    def status_color(self):
        """Durum rengini döndür"""
        colors = {
            'pending': 'warning',
            'approved': 'info',
            'running': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'cancelled': 'secondary',
        }
        return colors.get(self.status, 'secondary')

class TaskExecution(BaseModel):
    """Görev çalıştırma kayıtları"""
    task = models.ForeignKey(AutomationTask, on_delete=models.CASCADE, related_name='executions', verbose_name="Görev")
    ansible_job_id = models.CharField(max_length=100, blank=True, verbose_name="Ansible Job ID")
    stdout = models.TextField(blank=True, verbose_name="Standart Çıktı")
    stderr = models.TextField(blank=True, verbose_name="Hata Çıktısı")
    return_code = models.IntegerField(null=True, blank=True, verbose_name="Dönüş Kodu")
    execution_time = models.DurationField(null=True, blank=True, verbose_name="Çalışma Süresi")
    
    class Meta:
        verbose_name = "Görev Çalıştırma"
        verbose_name_plural = "Görev Çalıştırmalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.name} - {self.created_at}"

    @property
    def is_successful(self):
        """Çalıştırmanın başarılı olup olmadığını kontrol et"""
        return self.return_code == 0 if self.return_code is not None else False
