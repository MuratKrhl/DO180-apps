from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from core.models import BaseModel
import uuid

class Category(BaseModel):
    """Soru kategorileri"""
    name = models.CharField(max_length=100, verbose_name="Kategori Adı")
    slug = models.SlugField(unique=True, verbose_name="URL Slug")
    description = models.TextField(blank=True, verbose_name="Açıklama")
    icon = models.CharField(max_length=50, default='ri-question-line', verbose_name="İkon Sınıfı")
    order = models.PositiveIntegerField(default=0, verbose_name="Sıralama")
    color = models.CharField(max_length=20, default='primary', verbose_name="Renk Teması")

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('askgt:category_documents', kwargs={'category_slug': self.slug})

    def get_document_count(self):
        return self.documents.filter(is_active=True).count()

class Question(BaseModel):
    """Soru-Cevap modeli (Mevcut sistem)"""
    PRIORITY_CHOICES = [
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Soru Başlığı")
    question = models.TextField(verbose_name="Soru Detayı")
    answer = models.TextField(verbose_name="Cevap")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='questions', verbose_name="Kategori")
    tags = models.CharField(max_length=200, blank=True, verbose_name="Etiketler", help_text="Virgülle ayırın")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name="Öncelik")
    view_count = models.PositiveIntegerField(default=0, verbose_name="Görüntülenme Sayısı")
    is_featured = models.BooleanField(default=False, verbose_name="Öne Çıkan")

    class Meta:
        verbose_name = "Soru"
        verbose_name_plural = "Sorular"
        ordering = ['-is_featured', '-priority', '-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('askgt:question_detail', kwargs={'pk': self.pk})

    def get_tags_list(self):
        """Etiketleri liste olarak döndür"""
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    def increment_view_count(self):
        """Görüntülenme sayısını artır"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

class Document(BaseModel):
    """Harici doküman modeli - API'den çekilen dokümanlar"""
    DOCUMENT_TYPES = [
        ('technical', 'Teknik Doküman'),
        ('guide', 'Kullanım Kılavuzu'),
        ('troubleshooting', 'Sorun Giderme'),
        ('installation', 'Kurulum Rehberi'),
        ('configuration', 'Yapılandırma'),
        ('best_practices', 'En İyi Uygulamalar'),
        ('release_notes', 'Sürüm Notları'),
        ('api_docs', 'API Dokümantasyonu'),
    ]

    SOURCE_TYPES = [
        ('confluence', 'Confluence'),
        ('sharepoint', 'SharePoint'),
        ('wiki', 'Wiki'),
        ('external_api', 'Harici API'),
        ('manual', 'Manuel Giriş'),
    ]

    title = models.CharField(max_length=300, verbose_name="Doküman Başlığı")
    summary = models.TextField(max_length=500, blank=True, verbose_name="Özet")
    original_url = models.URLField(verbose_name="Orijinal URL")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='documents', verbose_name="Kategori")
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='technical', verbose_name="Doküman Tipi")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, default='external_api', verbose_name="Kaynak Tipi")
    
    # API Senkronizasyon alanları
    source_id = models.CharField(max_length=100, unique=True, verbose_name="Kaynak ID", help_text="API'den gelen unique ID")
    last_modified = models.DateTimeField(null=True, blank=True, verbose_name="Son Değişiklik")
    sync_date = models.DateTimeField(auto_now=True, verbose_name="Senkronizasyon Tarihi")
    
    # Metadata
    author = models.CharField(max_length=100, blank=True, verbose_name="Yazar")
    tags = models.CharField(max_length=300, blank=True, verbose_name="Etiketler")
    language = models.CharField(max_length=10, default='tr', verbose_name="Dil")
    view_count = models.PositiveIntegerField(default=0, verbose_name="Görüntülenme Sayısı")
    
    # Arama ve filtreleme
    content_preview = models.TextField(blank=True, verbose_name="İçerik Önizlemesi", help_text="Arama için kullanılır")
    is_featured = models.BooleanField(default=False, verbose_name="Öne Çıkan")
    is_external = models.BooleanField(default=True, verbose_name="Harici Doküman")

    class Meta:
        verbose_name = "Doküman"
        verbose_name_plural = "Dokümanlar"
        ordering = ['-is_featured', '-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['source_id']),
            models.Index(fields=['document_type']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('askgt:document_redirect', kwargs={'pk': self.pk})

    def get_tags_list(self):
        """Etiketleri liste olarak döndür"""
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

    def increment_view_count(self):
        """Görüntülenme sayısını artır"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

    def get_display_summary(self):
        """Görüntüleme için özet"""
        if self.summary:
            return self.summary
        elif self.content_preview:
            return self.content_preview[:200] + "..." if len(self.content_preview) > 200 else self.content_preview
        return "Özet mevcut değil"

class DocumentAccess(models.Model):
    """Doküman erişim logları"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    accessed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = "Doküman Erişimi"
        verbose_name_plural = "Doküman Erişimleri"
        ordering = ['-accessed_at']

class APISource(BaseModel):
    """API kaynak yapılandırması"""
    name = models.CharField(max_length=100, verbose_name="Kaynak Adı")
    api_url = models.URLField(verbose_name="API URL")
    api_key = models.CharField(max_length=200, blank=True, verbose_name="API Anahtarı")
    username = models.CharField(max_length=100, blank=True, verbose_name="Kullanıcı Adı")
    password = models.CharField(max_length=100, blank=True, verbose_name="Şifre")
    
    # Senkronizasyon ayarları
    sync_enabled = models.BooleanField(default=True, verbose_name="Senkronizasyon Aktif")
    sync_interval = models.PositiveIntegerField(default=60, verbose_name="Senkronizasyon Aralığı (dakika)")
    last_sync = models.DateTimeField(null=True, blank=True, verbose_name="Son Senkronizasyon")
    
    # Mapping ayarları
    title_field = models.CharField(max_length=50, default='title', verbose_name="Başlık Alanı")
    url_field = models.CharField(max_length=50, default='url', verbose_name="URL Alanı")
    category_field = models.CharField(max_length=50, default='category', verbose_name="Kategori Alanı")
    summary_field = models.CharField(max_length=50, default='summary', verbose_name="Özet Alanı")
    
    class Meta:
        verbose_name = "API Kaynağı"
        verbose_name_plural = "API Kaynakları"

    def __str__(self):
        return self.name
