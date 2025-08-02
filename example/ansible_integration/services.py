import requests
import json
import time
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from .models import JobTemplate, JobExecution, JobExecutionEvent, AnsibleConfiguration
import logging

logger = logging.getLogger(__name__)

class AnsibleTowerService:
    """Ansible Tower/AWX API servisi"""
    
    def __init__(self, config=None):
        if config is None:
            config = AnsibleConfiguration.objects.filter(is_default=True).first()
            if not config:
                raise ValueError("Varsayılan Ansible yapılandırması bulunamadı")
        
        self.config = config
        self.session = requests.Session()
        self.session.timeout = config.timeout
        self.session.verify = config.verify_ssl
        
        # Authentication
        if config.token:
            self.session.headers.update({'Authorization': f'Bearer {config.token}'})
        else:
            self.session.auth = (config.username, config.password)
    
    def sync_job_templates(self):
        """Job template'leri senkronize et"""
        try:
            url = f"{self.config.base_url}/api/v2/job_templates/"
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            templates = data.get('results', [])
            
            synced_count = 0
            for template_data in templates:
                template, created = self.sync_single_template(template_data)
                if template:
                    synced_count += 1
            
            logger.info(f"Job template senkronizasyonu tamamlandı: {synced_count} template")
            return synced_count
            
        except Exception as e:
            logger.error(f"Job template senkronizasyon hatası: {str(e)}")
            raise e
    
    def sync_single_template(self, template_data):
        """Tek template senkronizasyonu"""
        try:
            # Survey bilgilerini çek
            survey_spec = {}
            if template_data.get('survey_enabled'):
                survey_url = f"{self.config.base_url}/api/v2/job_templates/{template_data['id']}/survey_spec/"
                survey_response = self.session.get(survey_url)
                if survey_response.status_code == 200:
                    survey_spec = survey_response.json()
            
            template, created = JobTemplate.objects.update_or_create(
                tower_id=template_data['id'],
                defaults={
                    'name': template_data['name'],
                    'description': template_data.get('description', ''),
                    'job_type': template_data.get('job_type', 'run'),
                    'inventory_name': template_data.get('summary_fields', {}).get('inventory', {}).get('name', ''),
                    'project_name': template_data.get('summary_fields', {}).get('project', {}).get('name', ''),
                    'playbook': template_data.get('playbook', ''),
                    'credential_name': template_data.get('summary_fields', {}).get('credential', {}).get('name', ''),
                    'forks': template_data.get('forks', 5),
                    'limit': template_data.get('limit', ''),
                    'verbosity': template_data.get('verbosity', 0),
                    'extra_vars': template_data.get('extra_vars_dict', {}),
                    'job_tags': template_data.get('job_tags', ''),
                    'skip_tags': template_data.get('skip_tags', ''),
                    'survey_enabled': template_data.get('survey_enabled', False),
                    'survey_spec': survey_spec,
                    'last_sync': timezone.now(),
                    'is_active': True,
                }
            )
            
            return template, created
            
        except Exception as e:
            logger.error(f"Template senkronizasyon hatası {template_data.get('id')}: {str(e)}")
            return None, False
    
    def launch_job(self, job_template, extra_vars=None, limit=None, job_tags=None, skip_tags=None, user=None):
        """Job başlatma"""
        try:
            # Job execution kaydı oluştur
            job_execution = JobExecution.objects.create(
                job_template=job_template,
                extra_vars=extra_vars or {},
                limit=limit or '',
                job_tags=job_tags or '',
                skip_tags=skip_tags or '',
                created_by=user,
                status='pending'
            )
            
            # Launch payload hazırla
            payload = {}
            
            if extra_vars:
                payload['extra_vars'] = extra_vars
            if limit:
                payload['limit'] = limit
            if job_tags:
                payload['job_tags'] = job_tags
            if skip_tags:
                payload['skip_tags'] = skip_tags
            
            # API çağrısı
            url = f"{self.config.base_url}/api/v2/job_templates/{job_template.tower_id}/launch/"
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            launch_data = response.json()
            
            # Job execution güncelle
            job_execution.tower_job_id = launch_data['id']
            job_execution.status = launch_data.get('status', 'pending')
            job_execution.save()
            
            logger.info(f"Job başlatıldı: {job_template.name} (ID: {launch_data['id']})")
            return job_execution
            
        except Exception as e:
            logger.error(f"Job başlatma hatası: {str(e)}")
            if 'job_execution' in locals():
                job_execution.status = 'error'
                job_execution.stderr = str(e)
                job_execution.save()
            raise e
    
    def get_job_status(self, job_execution):
        """Job durumunu kontrol et"""
        if not job_execution.tower_job_id:
            return job_execution
        
        try:
            url = f"{self.config.base_url}/api/v2/jobs/{job_execution.tower_job_id}/"
            response = self.session.get(url)
            response.raise_for_status()
            
            job_data = response.json()
            
            # Durum güncelle
            job_execution.status = job_data.get('status', job_execution.status)
            
            if job_data.get('started'):
                job_execution.started_at = datetime.fromisoformat(
                    job_data['started'].replace('Z', '+00:00')
                )
            
            if job_data.get('finished'):
                job_execution.finished_at = datetime.fromisoformat(
                    job_data['finished'].replace('Z', '+00:00')
                )
                
                if job_execution.started_at and job_execution.finished_at:
                    job_execution.elapsed_time = job_execution.finished_at - job_execution.started_at
            
            job_execution.save()
            
            # Çıktıları çek
            if job_execution.is_finished:
                self.fetch_job_output(job_execution)
            
            return job_execution
            
        except Exception as e:
            logger.error(f"Job durum kontrolü hatası: {str(e)}")
            return job_execution
    
    def fetch_job_output(self, job_execution):
        """Job çıktılarını çek"""
        if not job_execution.tower_job_id:
            return
        
        try:
            # Stdout çek
            stdout_url = f"{self.config.base_url}/api/v2/jobs/{job_execution.tower_job_id}/stdout/"
            stdout_response = self.session.get(stdout_url, params={'format': 'txt'})
            if stdout_response.status_code == 200:
                job_execution.stdout = stdout_response.text
            
            # Job events çek
            events_url = f"{self.config.base_url}/api/v2/jobs/{job_execution.tower_job_id}/job_events/"
            events_response = self.session.get(events_url)
            if events_response.status_code == 200:
                events_data = events_response.json()
                self.sync_job_events(job_execution, events_data.get('results', []))
            
            job_execution.save()
            
        except Exception as e:
            logger.error(f"Job çıktı çekme hatası: {str(e)}")
    
    def sync_job_events(self, job_execution, events_data):
        """Job event'lerini senkronize et"""
        for event_data in events_data:
            JobExecutionEvent.objects.update_or_create(
                job_execution=job_execution,
                tower_event_id=event_data['id'],
                defaults={
                    'event_type': event_data.get('event', 'unknown'),
                    'event_data': event_data.get('event_data', {}),
                    'host': event_data.get('host_name', ''),
                    'task': event_data.get('task', ''),
                    'play': event_data.get('play', ''),
                    'stdout': event_data.get('stdout', ''),
                    'start_line': event_data.get('start_line', 0),
                    'end_line': event_data.get('end_line', 0),
                }
            )
    
    def cancel_job(self, job_execution):
        """Job'ı iptal et"""
        if not job_execution.tower_job_id or not job_execution.can_be_canceled:
            return False
        
        try:
            url = f"{self.config.base_url}/api/v2/jobs/{job_execution.tower_job_id}/cancel/"
            response = self.session.post(url)
            response.raise_for_status()
            
            job_execution.status = 'canceled'
            job_execution.save()
            
            logger.info(f"Job iptal edildi: {job_execution.tower_job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Job iptal etme hatası: {str(e)}")
            return False
    
    def test_connection(self):
        """Bağlantı testi"""
        try:
            url = f"{self.config.base_url}/api/v2/ping/"
            response = self.session.get(url)
            response.raise_for_status()
            
            return True, "Bağlantı başarılı"
            
        except Exception as e:
            return False, f"Bağlantı hatası: {str(e)}"
