import requests
import paramiko
import subprocess
import re
import json
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import KdbCertificate, JavaCertificate, CertificateAlert, CertificateNotificationSettings, CertificateSyncLog
import pyodbc
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

class CertificateService:
    """Sertifika yönetim servisleri"""
    
    @staticmethod
    def sync_kdb_from_appviewx():
        """AppViewX API'den KDB sertifikalarını senkronize et"""
        sync_log = CertificateSyncLog.objects.create(
            source='appviewx',
            certificate_type='kdb',
            status='running'
        )
        
        try:
            # AppViewX API yapılandırması
            api_base_url = getattr(settings, 'APPVIEWX_API_URL', '')
            api_token = getattr(settings, 'APPVIEWX_API_TOKEN', '')
            
            if not api_base_url or not api_token:
                raise Exception("AppViewX API yapılandırması eksik")
            
            headers = {
                'Authorization': f'Bearer {api_token}',
                'Content-Type': 'application/json'
            }
            
            # Sertifikaları çek
            response = requests.get(
                f"{api_base_url}/certificates",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            certificates_data = response.json()
            
            processed = 0
            successful = 0
            failed = 0
            new_count = 0
            updated_count = 0
            
            for cert_data in certificates_data.get('certificates', []):
                try:
                    processed += 1
                    
                    # Sertifika verilerini parse et
                    common_name = cert_data.get('commonName', '')
                    serial_number = cert_data.get('serialNumber', '')
                    
                    # Tarih formatını düzenle
                    valid_from = datetime.strptime(cert_data.get('validFrom'), '%Y-%m-%d %H:%M:%S')
                    valid_to = datetime.strptime(cert_data.get('validTo'), '%Y-%m-%d %H:%M:%S')
                    
                    # Sertifikayı güncelle veya oluştur
                    certificate, created = KdbCertificate.objects.update_or_create(
                        appviewx_id=cert_data.get('id'),
                        defaults={
                            'common_name': common_name,
                            'subject': cert_data.get('subject', ''),
                            'issuer': cert_data.get('issuer', ''),
                            'serial_number': serial_number,
                            'valid_from': timezone.make_aware(valid_from),
                            'valid_to': timezone.make_aware(valid_to),
                            'server_name': cert_data.get('serverName', ''),
                            'application_name': cert_data.get('applicationName', ''),
                            'environment': cert_data.get('environment', 'production'),
                            'kdb_file_path': cert_data.get('kdbPath', ''),
                            'certificate_label': cert_data.get('label', ''),
                            'appviewx_data': cert_data,
                            'data_source': 'appviewx',
                            'sync_source': 'appviewx_api'
                        }
                    )
                    
                    # Durumu güncelle
                    certificate.update_status()
                    
                    if created:
                        new_count += 1
                    else:
                        updated_count += 1
                    
                    successful += 1
                    
                except Exception as e:
                    failed += 1
                    logger.error(f"AppViewX sertifika işleme hatası: {e}")
            
            # Log'u güncelle
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.total_processed = processed
            sync_log.successful_count = successful
            sync_log.failed_count = failed
            sync_log.new_count = new_count
            sync_log.updated_count = updated_count
            sync_log.save()
            
            logger.info(f"AppViewX senkronizasyonu tamamlandı: {successful}/{processed}")
            return sync_log
            
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.error_details = str(e)
            sync_log.save()
            logger.error(f"AppViewX senkronizasyon hatası: {e}")
            raise
    
    @staticmethod
    def sync_kdb_from_sql_database():
        """SQL veritabanından KDB sertifikalarını senkronize et"""
        sync_log = CertificateSyncLog.objects.create(
            source='sql_db',
            certificate_type='kdb',
            status='running'
        )
        
        try:
            # SQL bağlantı ayarları
            db_config = getattr(settings, 'CERTIFICATE_SQL_DB', {})
            
            if not db_config:
                raise Exception("SQL veritabanı yapılandırması eksik")
            
            # SQLAlchemy engine oluştur
            connection_string = f"mssql+pyodbc://{db_config['user']}:{db_config['password']}@{db_config['server']}/{db_config['database']}?driver=ODBC+Driver+17+for+SQL+Server"
            engine = create_engine(connection_string)
            
            # Sertifika sorgusunu çalıştır
            query = """
            SELECT 
                CommonName,
                Subject,
                Issuer,
                SerialNumber,
                ValidFrom,
                ValidTo,
                ServerName,
                ApplicationName,
                Environment,
                KdbPath,
                CertificateLabel
            FROM CertificateInventory 
            WHERE IsActive = 1 AND CertificateType = 'KDB'
            """
            
            with engine.connect() as connection:
                result = connection.execute(text(query))
                
                processed = 0
                successful = 0
                failed = 0
                new_count = 0
                updated_count = 0
                
                for row in result:
                    try:
                        processed += 1
                        
                        # Sertifikayı güncelle veya oluştur
                        certificate, created = KdbCertificate.objects.update_or_create(
                            common_name=row.CommonName,
                            serial_number=row.SerialNumber,
                            server_name=row.ServerName,
                            defaults={
                                'subject': row.Subject or '',
                                'issuer': row.Issuer or '',
                                'valid_from': timezone.make_aware(row.ValidFrom),
                                'valid_to': timezone.make_aware(row.ValidTo),
                                'application_name': row.ApplicationName or '',
                                'environment': row.Environment or 'production',
                                'kdb_file_path': row.KdbPath or '',
                                'certificate_label': row.CertificateLabel or '',
                                'data_source': 'sql_db',
                                'sync_source': 'sql_database'
                            }
                        )
                        
                        certificate.update_status()
                        
                        if created:
                            new_count += 1
                        else:
                            updated_count += 1
                        
                        successful += 1
                        
                    except Exception as e:
                        failed += 1
                        logger.error(f"SQL sertifika işleme hatası: {e}")
            
            # Log'u güncelle
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.total_processed = processed
            sync_log.successful_count = successful
            sync_log.failed_count = failed
            sync_log.new_count = new_count
            sync_log.updated_count = updated_count
            sync_log.save()
            
            logger.info(f"SQL senkronizasyonu tamamlandı: {successful}/{processed}")
            return sync_log
            
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.error_details = str(e)
            sync_log.save()
            logger.error(f"SQL senkronizasyon hatası: {e}")
            raise
    
    @staticmethod
    def sync_java_certificates_from_keystore(server_info):
        """SSH ile sunuculara bağlanıp Java keystore'larını tara"""
        sync_log = CertificateSyncLog.objects.create(
            source='ssh_keytool',
            certificate_type='java',
            status='running'
        )
        
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            processed = 0
            successful = 0
            failed = 0
            new_count = 0
            updated_count = 0
            
            for server in server_info:
                try:
                    # SSH bağlantısı
                    ssh_client.connect(
                        hostname=server['host'],
                        username=server['username'],
                        password=server.get('password'),
                        key_filename=server.get('key_file'),
                        timeout=30
                    )
                    
                    # Keystore dosyalarını bul
                    find_command = f"find {server.get('search_path', '/opt')} -name '*.jks' -o -name '*.p12' -o -name '*.keystore' 2>/dev/null"
                    stdin, stdout, stderr = ssh_client.exec_command(find_command)
                    keystore_files = stdout.read().decode().strip().split('\n')
                    
                    for keystore_path in keystore_files:
                        if not keystore_path:
                            continue
                        
                        try:
                            processed += 1
                            
                            # Keytool ile sertifika bilgilerini al
                            keytool_command = f"keytool -list -v -keystore {keystore_path} -storepass {server.get('keystore_password', 'changeit')}"
                            stdin, stdout, stderr = ssh_client.exec_command(keytool_command)
                            keytool_output = stdout.read().decode()
                            
                            # Keytool çıktısını parse et
                            certificates = CertificateService.parse_keytool_output(keytool_output, keystore_path)
                            
                            for cert_data in certificates:
                                certificate, created = JavaCertificate.objects.update_or_create(
                                    keystore_path=keystore_path,
                                    alias_name=cert_data['alias'],
                                    ssh_host=server['host'],
                                    defaults={
                                        'common_name': cert_data['common_name'],
                                        'subject': cert_data['subject'],
                                        'issuer': cert_data['issuer'],
                                        'serial_number': cert_data['serial_number'],
                                        'valid_from': cert_data['valid_from'],
                                        'valid_to': cert_data['valid_to'],
                                        'server_name': server['host'],
                                        'application_name': server.get('application', ''),
                                        'environment': server.get('environment', 'production'),
                                        'keystore_type': cert_data['keystore_type'],
                                        'keytool_output': keytool_output,
                                        'ssh_user': server['username'],
                                        'sync_source': 'ssh_keytool'
                                    }
                                )
                                
                                certificate.update_status()
                                
                                if created:
                                    new_count += 1
                                else:
                                    updated_count += 1
                            
                            successful += 1
                            
                        except Exception as e:
                            failed += 1
                            logger.error(f"Keystore işleme hatası ({keystore_path}): {e}")
                    
                    ssh_client.close()
                    
                except Exception as e:
                    failed += 1
                    logger.error(f"SSH bağlantı hatası ({server['host']}): {e}")
            
            # Log'u güncelle
            sync_log.status = 'completed'
            sync_log.completed_at = timezone.now()
            sync_log.total_processed = processed
            sync_log.successful_count = successful
            sync_log.failed_count = failed
            sync_log.new_count = new_count
            sync_log.updated_count = updated_count
            sync_log.save()
            
            logger.info(f"Java keystore senkronizasyonu tamamlandı: {successful}/{processed}")
            return sync_log
            
        except Exception as e:
            sync_log.status = 'failed'
            sync_log.completed_at = timezone.now()
            sync_log.error_details = str(e)
            sync_log.save()
            logger.error(f"Java keystore senkronizasyon hatası: {e}")
            raise
    
    @staticmethod
    def parse_keytool_output(output, keystore_path):
        """Keytool çıktısını parse et"""
        certificates = []
        
        # Alias'ları bul
        alias_pattern = r'Alias name: (.+)'
        aliases = re.findall(alias_pattern, output)
        
        # Her alias için sertifika bilgilerini çıkar
        for alias in aliases:
            try:
                # Alias bölümünü bul
                alias_section = re.search(
                    rf'Alias name: {re.escape(alias)}.*?(?=Alias name:|$)', 
                    output, 
                    re.DOTALL
                )
                
                if not alias_section:
                    continue
                
                section_text = alias_section.group(0)
                
                # Sertifika bilgilerini çıkar
                cert_data = {
                    'alias': alias,
                    'keystore_type': 'jks',  # Default
                    'common_name': '',
                    'subject': '',
                    'issuer': '',
                    'serial_number': '',
                    'valid_from': None,
                    'valid_to': None,
                }
                
                # CN çıkar
                cn_match = re.search(r'CN=([^,]+)', section_text)
                if cn_match:
                    cert_data['common_name'] = cn_match.group(1).strip()
                
                # Subject çıkar
                subject_match = re.search(r'Owner: (.+)', section_text)
                if subject_match:
                    cert_data['subject'] = subject_match.group(1).strip()
                
                # Issuer çıkar
                issuer_match = re.search(r'Issuer: (.+)', section_text)
                if issuer_match:
                    cert_data['issuer'] = issuer_match.group(1).strip()
                
                # Serial number çıkar
                serial_match = re.search(r'Serial number: (.+)', section_text)
                if serial_match:
                    cert_data['serial_number'] = serial_match.group(1).strip()
                
                # Valid from çıkar
                valid_from_match = re.search(r'Valid from: (.+?) until:', section_text)
                if valid_from_match:
                    try:
                        valid_from_str = valid_from_match.group(1).strip()
                        cert_data['valid_from'] = timezone.make_aware(
                            datetime.strptime(valid_from_str, '%a %b %d %H:%M:%S %Z %Y')
                        )
                    except:
                        pass
                
                # Valid to çıkar
                valid_to_match = re.search(r'until: (.+)', section_text)
                if valid_to_match:
                    try:
                        valid_to_str = valid_to_match.group(1).strip()
                        cert_data['valid_to'] = timezone.make_aware(
                            datetime.strptime(valid_to_str, '%a %b %d %H:%M:%S %Z %Y')
                        )
                    except:
                        pass
                
                # Keystore tipini dosya uzantısından belirle
                if keystore_path.endswith('.p12'):
                    cert_data['keystore_type'] = 'pkcs12'
                elif keystore_path.endswith('.jceks'):
                    cert_data['keystore_type'] = 'jceks'
                
                certificates.append(cert_data)
                
            except Exception as e:
                logger.error(f"Keytool parse hatası (alias: {alias}): {e}")
        
        return certificates

class NotificationService:
    """Sertifika bildirim servisleri"""
    
    @staticmethod
    def check_expiring_certificates():
        """Süresi yaklaşan sertifikaları kontrol et ve uyarı oluştur"""
        today = timezone.now().date()
        
        # Uyarı günleri
        alert_days = [90, 60, 30, 15, 7, 1]
        
        for days in alert_days:
            target_date = today + timedelta(days=days)
            
            # KDB sertifikaları
            kdb_certs = KdbCertificate.objects.filter(
                is_active=True,
                valid_to__date=target_date
            )
            
            for cert in kdb_certs:
                NotificationService.create_and_send_alert(cert, 'kdb', f'expiring_{days}')
            
            # Java sertifikaları
            java_certs = JavaCertificate.objects.filter(
                is_active=True,
                valid_to__date=target_date
            )
            
            for cert in java_certs:
                NotificationService.create_and_send_alert(cert, 'java', f'expiring_{days}')
        
        # Süresi dolmuş sertifikalar
        expired_kdb = KdbCertificate.objects.filter(
            is_active=True,
            valid_to__date__lt=today,
            status__in=['valid', 'expiring']
        )
        
        for cert in expired_kdb:
            cert.update_status()
            NotificationService.create_and_send_alert(cert, 'kdb', 'expired')
        
        expired_java = JavaCertificate.objects.filter(
            is_active=True,
            valid_to__date__lt=today,
            status__in=['valid', 'expiring']
        )
        
        for cert in expired_java:
            cert.update_status()
            NotificationService.create_and_send_alert(cert, 'java', 'expired')
    
    @staticmethod
    def create_and_send_alert(certificate, cert_type, alert_type):
        """Uyarı oluştur ve e-posta gönder"""
        try:
            # Uyarı kaydını oluştur veya güncelle
            alert, created = CertificateAlert.objects.get_or_create(
                certificate_type=cert_type,
                certificate_id=certificate.id,
                alert_type=alert_type,
                defaults={
                    'certificate_common_name': certificate.common_name,
                    'expiry_date': certificate.valid_to,
                    'status': 'pending'
                }
            )
            
            if not created and alert.status == 'sent':
                return  # Zaten gönderilmiş
            
            # Bildirim ayarlarını al
            notification_settings = CertificateNotificationSettings.objects.filter(
                is_active=True
            )
            
            for setting in notification_settings:
                # Filtreleme kontrolü
                if not NotificationService.should_send_notification(certificate, cert_type, setting):
                    continue
                
                # E-posta gönder
                success = NotificationService.send_certificate_alert_email(
                    certificate, cert_type, alert_type, setting
                )
                
                if success:
                    alert.status = 'sent'
                    alert.sent_at = timezone.now()
                    alert.sent_to = '\n'.join(setting.recipient_emails.split('\n'))
                else:
                    alert.status = 'failed'
                    alert.error_message = 'E-posta gönderimi başarısız'
                
                alert.save()
            
        except Exception as e:
            logger.error(f"Uyarı oluşturma hatası: {e}")
    
    @staticmethod
    def should_send_notification(certificate, cert_type, setting):
        """Bildirim gönderilmeli mi kontrol et"""
        # Ortam kontrolü
        if setting.environments and certificate.environment not in setting.environments:
            return False
        
        # Sertifika tipi kontrolü
        if setting.certificate_types and cert_type not in setting.certificate_types:
            return False
        
        # Uygulama kontrolü
        if setting.applications and certificate.application_name not in setting.applications:
            return False
        
        return True
    
    @staticmethod
    def send_certificate_alert_email(certificate, cert_type, alert_type, setting):
        """Sertifika uyarı e-postası gönder"""
        try:
            # E-posta içeriğini hazırla
            context = {
                'certificate': certificate,
                'cert_type': cert_type.upper(),
                'alert_type': alert_type,
                'days_until_expiry': certificate.days_until_expiry,
                'is_expired': certificate.is_expired,
            }
            
            # Template'leri render et
            subject = render_to_string('certificates/emails/alert_subject.txt', context).strip()
            text_content = render_to_string('certificates/emails/alert_email.txt', context)
            html_content = render_to_string('certificates/emails/alert_email.html', context)
            
            # E-posta gönder
            recipient_list = [email.strip() for email in setting.recipient_emails.split('\n') if email.strip()]
            cc_list = [email.strip() for email in setting.cc_emails.split('\n') if email.strip()] if setting.cc_emails else []
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list,
                cc=cc_list
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            logger.info(f"Sertifika uyarı e-postası gönderildi: {certificate.common_name}")
            return True
            
        except Exception as e:
            logger.error(f"E-posta gönderim hatası: {e}")
            return False
    
    @staticmethod
    def send_certificate_summary_report():
        """Haftalık sertifika özet raporu gönder"""
        try:
            today = timezone.now().date()
            
            # Özet istatistikleri hazırla
            stats = {
                'total_kdb': KdbCertificate.objects.filter(is_active=True).count(),
                'total_java': JavaCertificate.objects.filter(is_active=True).count(),
                'expired_kdb': KdbCertificate.objects.filter(is_active=True, status='expired').count(),
                'expired_java': JavaCertificate.objects.filter(is_active=True, status='expired').count(),
                'expiring_30_kdb': KdbCertificate.objects.filter(
                    is_active=True, 
                    valid_to__date__lte=today + timedelta(days=30),
                    valid_to__date__gte=today
                ).count(),
                'expiring_30_java': JavaCertificate.objects.filter(
                    is_active=True, 
                    valid_to__date__lte=today + timedelta(days=30),
                    valid_to__date__gte=today
                ).count(),
            }
            
            # Yaklaşan sertifikaları al
            expiring_kdb = KdbCertificate.objects.filter(
                is_active=True,
                valid_to__date__lte=today + timedelta(days=30),
                valid_to__date__gte=today
            ).order_by('valid_to')[:10]
            
            expiring_java = JavaCertificate.objects.filter(
                is_active=True,
                valid_to__date__lte=today + timedelta(days=30),
                valid_to__date__gte=today
            ).order_by('valid_to')[:10]
            
            context = {
                'stats': stats,
                'expiring_kdb': expiring_kdb,
                'expiring_java': expiring_java,
                'report_date': today,
            }
            
            # Bildirim ayarlarını al
            notification_settings = CertificateNotificationSettings.objects.filter(
                is_active=True,
                send_weekly_report=True
            )
            
            for setting in notification_settings:
                # Template'leri render et
                subject = render_to_string('certificates/emails/weekly_report_subject.txt', context).strip()
                text_content = render_to_string('certificates/emails/weekly_report.txt', context)
                html_content = render_to_string('certificates/emails/weekly_report.html', context)
                
                # E-posta gönder
                recipient_list = [email.strip() for email in setting.recipient_emails.split('\n') if email.strip()]
                
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=recipient_list
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
            
            logger.info("Haftalık sertifika raporu gönderildi")
            
        except Exception as e:
            logger.error(f"Haftalık rapor gönderim hatası: {e}")
