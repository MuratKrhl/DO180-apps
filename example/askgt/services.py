import requests
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import Document, Category, APISource, DocumentAccess
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class DocumentSyncService:
    """Doküman senkronizasyon servisi"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30
    
    def sync_all_sources(self) -> Dict[str, int]:
        """Tüm aktif API kaynaklarından doküman çek"""
        results = {}
        
        for source in APISource.objects.filter(is_active=True, sync_enabled=True):
            try:
                count = self.sync_from_source(source)
                results[source.name] = count
                
                # Son senkronizasyon tarihini güncelle
                source.last_sync = timezone.now()
                source.save(update_fields=['last_sync'])
                
                logger.info(f"Synced {count} documents from {source.name}")
                
            except Exception as e:
                logger.error(f"Error syncing from {source.name}: {str(e)}")
                results[source.name] = 0
        
        return results
    
    def sync_from_source(self, source: APISource) -> int:
        """Belirli bir kaynaktan doküman çek"""
        if source.name.lower() == 'confluence':
            return self._sync_confluence(source)
        elif source.name.lower() == 'sharepoint':
            return self._sync_sharepoint(source)
        elif source.name.lower() == 'wiki':
            return self._sync_wiki(source)
        else:
            return self._sync_generic_api(source)
    
    def _sync_confluence(self, source: APISource) -> int:
        """Confluence API'den doküman çek"""
        headers = {
            'Authorization': f'Bearer {source.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Confluence REST API endpoint
        url = f"{source.api_url}/rest/api/content"
        params = {
            'expand': 'body.storage,space,version',
            'limit': 100,
            'type': 'page'
        }
        
        try:
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            documents_created = 0
            
            for item in data.get('results', []):
                doc_data = self._parse_confluence_item(item, source)
                if self._create_or_update_document(doc_data, source):
                    documents_created += 1
            
            return documents_created
            
        except requests.RequestException as e:
            logger.error(f"Confluence API error: {str(e)}")
            raise
    
    def _sync_sharepoint(self, source: APISource) -> int:
        """SharePoint API'den doküman çek"""
        headers = {
            'Authorization': f'Bearer {source.api_key}',
            'Accept': 'application/json'
        }
        
        # SharePoint Graph API endpoint
        url = f"{source.api_url}/sites/root/lists/Documents/items"
        params = {
            'expand': 'fields',
            '$top': 100
        }
        
        try:
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            documents_created = 0
            
            for item in data.get('value', []):
                doc_data = self._parse_sharepoint_item(item, source)
                if self._create_or_update_document(doc_data, source):
                    documents_created += 1
            
            return documents_created
            
        except requests.RequestException as e:
            logger.error(f"SharePoint API error: {str(e)}")
            raise
    
    def _sync_wiki(self, source: APISource) -> int:
        """Wiki API'den doküman çek"""
        headers = {
            'User-Agent': 'MiddlewarePortal/1.0',
            'Authorization': f'Bearer {source.api_key}' if source.api_key else None
        }
        
        # MediaWiki API endpoint
        url = f"{source.api_url}/api.php"
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'allpages',
            'aplimit': 100,
            'apnamespace': 0
        }
        
        try:
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            documents_created = 0
            
            for item in data.get('query', {}).get('allpages', []):
                doc_data = self._parse_wiki_item(item, source)
                if self._create_or_update_document(doc_data, source):
                    documents_created += 1
            
            return documents_created
            
        except requests.RequestException as e:
            logger.error(f"Wiki API error: {str(e)}")
            raise
    
    def _sync_generic_api(self, source: APISource) -> int:
        """Genel API'den doküman çek"""
        headers = {
            'Authorization': f'Bearer {source.api_key}' if source.api_key else None,
            'Content-Type': 'application/json'
        }
        
        if source.username and source.password:
            auth = (source.username, source.password)
        else:
            auth = None
        
        try:
            response = self.session.get(source.api_url, headers=headers, auth=auth)
            response.raise_for_status()
            
            data = response.json()
            documents_created = 0
            
            # API'den gelen veri formatına göre parse et
            items = data if isinstance(data, list) else data.get('items', data.get('results', []))
            
            for item in items:
                doc_data = self._parse_generic_item(item, source)
                if self._create_or_update_document(doc_data, source):
                    documents_created += 1
            
            return documents_created
            
        except requests.RequestException as e:
            logger.error(f"Generic API error: {str(e)}")
            raise
    
    def _parse_confluence_item(self, item: Dict, source: APISource) -> Dict:
        """Confluence item'ını parse et"""
        return {
            'source_id': f"confluence_{item['id']}",
            'title': item.get('title', 'Başlıksız'),
            'original_url': f"{source.api_url.rstrip('/rest/api/content')}/pages/viewpage.action?pageId={item['id']}",
            'summary': self._extract_text_from_html(item.get('body', {}).get('storage', {}).get('value', '')),
            'author': item.get('version', {}).get('by', {}).get('displayName', ''),
            'last_modified': self._parse_date(item.get('version', {}).get('when')),
            'category_name': item.get('space', {}).get('name', 'Genel'),
            'source_type': 'confluence',
            'content_preview': self._extract_text_from_html(item.get('body', {}).get('storage', {}).get('value', ''))[:500]
        }
    
    def _parse_sharepoint_item(self, item: Dict, source: APISource) -> Dict:
        """SharePoint item'ını parse et"""
        fields = item.get('fields', {})
        return {
            'source_id': f"sharepoint_{item['id']}",
            'title': fields.get('Title', 'Başlıksız'),
            'original_url': fields.get('FileRef', ''),
            'summary': fields.get('Description', ''),
            'author': fields.get('Author', {}).get('DisplayName', ''),
            'last_modified': self._parse_date(fields.get('Modified')),
            'category_name': fields.get('Category', 'Genel'),
            'source_type': 'sharepoint',
            'content_preview': fields.get('Description', '')[:500]
        }
    
    def _parse_wiki_item(self, item: Dict, source: APISource) -> Dict:
        """Wiki item'ını parse et"""
        return {
            'source_id': f"wiki_{item['pageid']}",
            'title': item.get('title', 'Başlıksız'),
            'original_url': f"{source.api_url.rstrip('/api.php')}/index.php?title={item.get('title', '').replace(' ', '_')}",
            'summary': '',
            'author': '',
            'last_modified': None,
            'category_name': 'Wiki',
            'source_type': 'wiki',
            'content_preview': ''
        }
    
    def _parse_generic_item(self, item: Dict, source: APISource) -> Dict:
        """Genel API item'ını parse et"""
        return {
            'source_id': f"generic_{item.get('id', item.get('uuid', str(hash(str(item)))))}",
            'title': item.get(source.title_field, item.get('title', 'Başlıksız')),
            'original_url': item.get(source.url_field, item.get('url', '')),
            'summary': item.get(source.summary_field, item.get('summary', item.get('description', ''))),
            'author': item.get('author', item.get('creator', '')),
            'last_modified': self._parse_date(item.get('updated_at', item.get('modified'))),
            'category_name': item.get(source.category_field, item.get('category', 'Genel')),
            'source_type': 'external_api',
            'content_preview': item.get('content', item.get('body', ''))[:500]
        }
    
    def _create_or_update_document(self, doc_data: Dict, source: APISource) -> bool:
        """Doküman oluştur veya güncelle"""
        try:
            # Kategori bul veya oluştur
            category, created = Category.objects.get_or_create(
                name=doc_data['category_name'],
                defaults={
                    'slug': self._slugify_category(doc_data['category_name']),
                    'description': f"{doc_data['category_name']} kategorisi",
                    'icon': 'ri-file-text-line'
                }
            )
            
            # Doküman oluştur veya güncelle
            document, created = Document.objects.update_or_create(
                source_id=doc_data['source_id'],
                defaults={
                    'title': doc_data['title'],
                    'original_url': doc_data['original_url'],
                    'summary': doc_data['summary'],
                    'category': category,
                    'author': doc_data['author'],
                    'last_modified': doc_data['last_modified'],
                    'source_type': doc_data['source_type'],
                    'content_preview': doc_data['content_preview'],
                    'is_active': True
                }
            )
            
            return created
            
        except Exception as e:
            logger.error(f"Error creating/updating document {doc_data['source_id']}: {str(e)}")
            return False
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """HTML'den metin çıkar"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(strip=True)[:500]
        except ImportError:
            # BeautifulSoup yoksa basit regex kullan
            import re
            clean = re.compile('<.*?>')
            return re.sub(clean, '', html_content)[:500]
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Tarih string'ini parse et"""
        if not date_str:
            return None
        
        try:
            # ISO format
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except:
            try:
                # Diğer formatlar
                return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            except:
                return None
    
    def _slugify_category(self, name: str) -> str:
        """Kategori adından slug oluştur"""
        from django.utils.text import slugify
        return slugify(name)

class DocumentAnalyticsService:
    """Doküman analitik servisi"""
    
    @staticmethod
    def log_document_access(document: Document, user, request):
        """Doküman erişimini logla"""
        DocumentAccess.objects.create(
            document=document,
            user=user,
            ip_address=DocumentAnalyticsService.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        # Görüntülenme sayısını artır
        document.increment_view_count()
    
    @staticmethod
    def get_client_ip(request):
        """Client IP adresini al"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def get_popular_documents(limit: int = 10) -> List[Document]:
        """Popüler dokümanları getir"""
        return Document.objects.filter(is_active=True).order_by('-view_count')[:limit]
    
    @staticmethod
    def get_recent_documents(limit: int = 10) -> List[Document]:
        """Son eklenen dokümanları getir"""
        return Document.objects.filter(is_active=True).order_by('-created_at')[:limit]
    
    @staticmethod
    def get_category_stats() -> Dict:
        """Kategori istatistikleri"""
        from django.db.models import Count
        return Category.objects.filter(is_active=True).annotate(
            document_count=Count('documents', filter=models.Q(documents__is_active=True))
        ).order_by('-document_count')
