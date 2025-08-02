from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import BaseModel
import json

class JobTemplate(BaseModel):
    """Ansible Job Template modeli"""
    TEMPLATE_TYPES = [
        ('playbook', 'Playbook'),
        ('workflow', 'Workflow'),
        ('inventory_sync', 'Inventory Sync'),
        ('project_sync', 'Project Sync'),
    ]
    
    VERBOSITY_CHOICES = [
        (0, 'Normal'),
        (1, 'Verbose'),
        (2, 'More Verbose'),
        (3, 'Debug'),
        (4, 'Connection Debug'),
    ]
    
    # Ansible Tower/AWX fields
    tower_id = models.PositiveIntegerField(unique=True, verbose_name="Tower/AWX ID")
    name = models.CharField(max_length=200, verbose_name="Template Adı")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    job_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, default='playbook', verbose_name="Job Tipi")
    inventory_name = models.CharField(max_length=200, blank=True, verbose_name="Inventory")
    project_name = models.CharField(max_length=200, blank=True, verbose_name="Proje")
    playbook = models.CharField(max_length=500, blank=True, verbose_name="Playbook")
    credential_name = models.CharField(max_length=200, blank=True, verbose_name="Credential")
    
    # Execution settings
    forks = models.PositiveIntegerField(default=5, verbose_name="Fork Sayısı")
    limit = models.CharField(max_length=500, blank=True, verbose_name="Limit")
    verbosity = models.PositiveIntegerField(choices=VERBOSITY_CHOICES, default=0, verbose_name="Verbosity")
    extra_vars = models.JSONField(default=dict, blank=True, verbose_name="Extra Variables")
    job_tags = models.CharField(max_length=500, blank=True, verbose_name="Job Tags")
    skip_tags = models.CharField(max_length=500, blank=True, verbose_name="Skip Tags")
    
    # Survey/Form fields
    survey_enabled = models.BooleanField(default=False, verbose_name="Survey Aktif")
    survey_spec = models.JSONField(default=dict, blank=True, verbose_name="Survey Specification")
    
    # Permissions and access
    allowed_users = models.ManyToManyField(User, blank=True, verbose_name="İzinli Kullanıcılar")
    allowed_groups = models.ManyToManyField('auth.Group', blank=True, verbose_name="İzinli Gruplar")
    requires_approval = models.BooleanField(default=False, verbose_name="Onay Gerektirir")
    is_dangerous = models.BooleanField(default=False, verbose_name="Tehlikeli İşlem")
    
    # Metadata
    last_sync = models.DateTimeField(null=True, blank=True, verbose_name="Son Senkronizasyon")
    last_job_run = models.DateTimeField(null=True, blank=True, verbose_name="Son Çalıştırma")
    success_count = models.PositiveIntegerField(default=0, verbose_name="Başarılı Çalıştırma")
    failed_count = models.PositiveIntegerField(default=0, verbose_name="Başarısız Çalıştırma")
    
    class Meta:
        verbose_name = "Job Template"
        verbose_name_plural = "Job Template'ler"
        ordering = ['name']
        indexes = [
            models.Index(fields=['tower_id']),
            models.Index(fields=['name']),
            models.Index(fields=['job_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_job_type_display()})"
    
    @property
    def success_rate(self):
        """Başarı oranı"""
        total = self.success_count + self.failed_count
        if total == 0:
            return 0
        return round((self.success_count / total) * 100, 1)
    
    def can_user_execute(self, user):
        """Kullanıcının çalıştırma yetkisi var mı?"""
        if user.is_superuser:
            return True
        
        if self.allowed_users.filter(id=user.id).exists():
            return True
        
        if self.allowed_groups.filter(user__in=[user]).exists():
            return True
        
        return False
    
    def get_survey_fields(self):
        """Survey alanlarını döndür"""
        if not self.survey_enabled or not self.survey_spec:
            return []
        
        return self.survey_spec.get('spec', [])

class JobExecution(BaseModel):
    """Job çalıştırma kayıtları"""
    STATUS_CHOICES = [
        ('pending', 'Bekliyor'),
        ('waiting', 'Sırada'),
        ('running', 'Çalışıyor'),
        ('successful', 'Başarılı'),
        ('failed', 'Başarısız'),
        ('error', 'Hata'),
        ('canceled', 'İptal Edildi'),
    ]
    
    job_template = models.ForeignKey(JobTemplate, on_delete=models.CASCADE, verbose_name="Job Template")
    tower_job_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="Tower Job ID")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Durum")
    
    # Execution details
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Başlangıç")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Bitiş")
    elapsed_time = models.DurationField(null=True, blank=True, verbose_name="Süre")
    
    # Parameters
    extra_vars = models.JSONField(default=dict, blank=True, verbose_name="Extra Variables")
    limit = models.CharField(max_length=500, blank=True, verbose_name="Limit")
    job_tags = models.CharField(max_length=500, blank=True, verbose_name="Job Tags")
    skip_tags = models.CharField(max_length=500, blank=True, verbose_name="Skip Tags")
    
    # Results
    stdout = models.TextField(blank=True, verbose_name="Standart Çıktı")
    stderr = models.TextField(blank=True, verbose_name="Hata Çıktısı")
    result_stdout = models.TextField(blank=True, verbose_name="Sonuç Çıktısı")
    
    # Approval workflow
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='approved_jobs', verbose_name="Onaylayan")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Onay Tarihi")
    approval_notes = models.TextField(blank=True, verbose_name="Onay Notları")
    
    class Meta:
        verbose_name = "Job Çalıştırma"
        verbose_name_plural = "Job Çalıştırmalar"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tower_job_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.job_template.name} - {self.get_status_display()} ({self.created_at})"
    
    @property
    def status_color(self):
        """Durum rengi"""
        colors = {
            'pending': 'secondary',
            'waiting': 'info',
            'running': 'primary',
            'successful': 'success',
            'failed': 'danger',
            'error': 'danger',
            'canceled': 'warning',
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def can_be_canceled(self):
        """İptal edilebilir mi?"""
        return self.status in ['pending', 'waiting', 'running']
    
    @property
    def is_finished(self):
        """Tamamlandı mı?"""
        return self.status in ['successful', 'failed', 'error', 'canceled']

class JobExecutionEvent(BaseModel):
    """Job çalıştırma olayları"""
    EVENT_TYPES = [
        ('playbook_on_start', 'Playbook Başladı'),
        ('playbook_on_play_start', 'Play Başladı'),
        ('playbook_on_task_start', 'Task Başladı'),
        ('runner_on_ok', 'Task Başarılı'),
        ('runner_on_failed', 'Task Başarısız'),
        ('runner_on_skipped', 'Task Atlandı'),
        ('runner_on_unreachable', 'Host Erişilemez'),
        ('playbook_on_stats', 'İstatistikler'),
        ('error', 'Hata'),
    ]
    
    job_execution = models.ForeignKey(JobExecution, on_delete=models.CASCADE, 
                                    related_name='events', verbose_name="Job Çalıştırma")
    tower_event_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="Tower Event ID")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, verbose_name="Olay Tipi")
    event_data = models.JSONField(default=dict, verbose_name="Olay Verisi")
    host = models.CharField(max_length=200, blank=True, verbose_name="Host")
    task = models.CharField(max_length=500, blank=True, verbose_name="Task")
    play = models.CharField(max_length=500, blank=True, verbose_name="Play")
    stdout = models.TextField(blank=True, verbose_name="Çıktı")
    start_line = models.PositiveIntegerField(default=0, verbose_name="Başlangıç Satırı")
    end_line = models.PositiveIntegerField(default=0, verbose_name="Bitiş Satırı")
    
    class Meta:
        verbose_name = "Job Olayı"
        verbose_name_plural = "Job Olayları"
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['job_execution', 'created_at']),
            models.Index(fields=['event_type']),
        ]
    
    def __str__(self):
        return f"{self.job_execution} - {self.get_event_type_display()}"

class AnsibleConfiguration(BaseModel):
    """Ansible Tower/AWX yapılandırması"""
    name = models.CharField(max_length=100, verbose_name="Yapılandırma Adı")
    base_url = models.URLField(verbose_name="Base URL")
    username = models.CharField(max_length=100, verbose_name="Kullanıcı Adı")
    password = models.CharField(max_length=100, verbose_name="Şifre")
    token = models.CharField(max_length=200, blank=True, verbose_name="API Token")
    verify_ssl = models.BooleanField(default=True, verbose_name="SSL Doğrulama")
    timeout = models.PositiveIntegerField(default=30, verbose_name="Timeout (saniye)")
    is_default = models.BooleanField(default=False, verbose_name="Varsayılan")
    
    class Meta:
        verbose_name = "Ansible Yapılandırması"
        verbose_name_plural = "Ansible Yapılandırmaları"
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Sadece bir tane varsayılan olabilir
        if self.is_default:
            AnsibleConfiguration.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
