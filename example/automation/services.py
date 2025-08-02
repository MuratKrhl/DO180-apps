import subprocess
import json
import os
import tempfile
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import AutomationTask, TaskExecution
import logging

logger = logging.getLogger(__name__)

class AnsibleService:
    """Ansible işlemlerini yöneten servis"""
    
    def __init__(self):
        self.ansible_playbook_cmd = getattr(settings, 'ANSIBLE_PLAYBOOK_CMD', 'ansible-playbook')
        self.ansible_base_path = getattr(settings, 'ANSIBLE_BASE_PATH', '/opt/ansible')
        
    def execute_task(self, task_id):
        """Görevi çalıştır"""
        try:
            task = AutomationTask.objects.get(id=task_id)
            
            if not task.can_be_executed:
                raise Exception(f"Görev çalıştırılamaz. Durum: {task.get_status_display()}")
            
            # Görev durumunu güncelle
            task.status = 'running'
            task.started_at = timezone.now()
            task.save()
            
            # Çalıştırma kaydı oluştur
            execution = TaskExecution.objects.create(
                task=task,
                created_by=task.created_by
            )
            
            # Ansible komutunu hazırla
            cmd = self._build_ansible_command(task)
            
            logger.info(f"Ansible komutu çalıştırılıyor: {' '.join(cmd)}")
            
            # Komutu çalıştır
            start_time = timezone.now()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 saat timeout
            )
            end_time = timezone.now()
            
            # Sonuçları kaydet
            execution.stdout = result.stdout
            execution.stderr = result.stderr
            execution.return_code = result.returncode
            execution.execution_time = end_time - start_time
            execution.save()
            
            # Görev durumunu güncelle
            task.status = 'completed' if result.returncode == 0 else 'failed'
            task.completed_at = end_time
            task.save()
            
            logger.info(f"Görev tamamlandı: {task.name}, Return Code: {result.returncode}")
            
            return execution
            
        except Exception as e:
            logger.error(f"Görev çalıştırma hatası: {str(e)}")
            
            # Hata durumunda görev durumunu güncelle
            if 'task' in locals():
                task.status = 'failed'
                task.completed_at = timezone.now()
                task.save()
            
            raise e
    
    def _build_ansible_command(self, task):
        """Ansible komutunu oluştur"""
        cmd = [self.ansible_playbook_cmd]
        
        # Playbook dosyası
        playbook_path = os.path.join(self.ansible_base_path, task.playbook_template.playbook_path)
        cmd.append(playbook_path)
        
        # Inventory dosyası
        if task.playbook_template.inventory_path:
            inventory_path = os.path.join(self.ansible_base_path, task.playbook_template.inventory_path)
            cmd.extend(['-i', inventory_path])
        
        # Değişkenler
        if task.variables:
            for key, value in task.variables.items():
                cmd.extend(['-e', f"{key}={value}"])
        
        # Hedef sunucular (limit)
        if task.target_servers.exists():
            server_list = ','.join([server.hostname for server in task.target_servers.all()])
            cmd.extend(['--limit', server_list])
        
        # Ek parametreler
        cmd.extend(['-v'])  # Verbose output
        
        return cmd
    
    def validate_playbook(self, playbook_path):
        """Playbook'un geçerli olup olmadığını kontrol et"""
        try:
            full_path = os.path.join(self.ansible_base_path, playbook_path)
            
            if not os.path.exists(full_path):
                return False, f"Playbook dosyası bulunamadı: {full_path}"
            
            # Syntax check
            cmd = [self.ansible_playbook_cmd, '--syntax-check', full_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"Syntax hatası: {result.stderr}"
            
            return True, "Playbook geçerli"
            
        except Exception as e:
            return False, f"Doğrulama hatası: {str(e)}"

# Celery task (eğer async çalıştırma istenirse)
def execute_ansible_task_async(task_id):
    """Ansible görevini asenkron olarak çalıştır"""
    service = AnsibleService()
    return service.execute_task(task_id)
