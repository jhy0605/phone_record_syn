from celery import shared_task
from django.utils import timezone
from .models import Device, SyncRecord
from record_syn.services import add_credentials, copy_file
import os


# 检查设备SMB共享是否可访问
@shared_task
def check_device_status(device_id):
    device = Device.objects.get(id=device_id)
    if device.status != 'syncing':
        disk_b = {
            "ip": device.ip_address,
            'user': device.smb_username,
            "passwd": device.smb_password,
        }
        add_credentials([disk_b])
        if os.path.exists(device.remote_path):
            device.status = 'online'
        else:
            device.status = 'offline'

        device.last_online_time = timezone.now()
        device.save()
        print('{}：{}'.format(device.ip_address, device.status))
        return device.status


@shared_task
def sync_device_files(device_id):
    device = Device.objects.get(id=device_id)
    device.status = 'syncing'
    device.save()

    start_time = timezone.now()

    # 添加203凭据
    disk_a = {
        "ip": "10.10.100.203",
        'user': "JW\\record_syn",
        "passwd": "Admin@1234", }
    add_credentials([disk_a])

    # 同步文件
    file_count = copy_file(device.remote_path, device.local_path, device)
    if file_count > 0:
        # 创建同步记录（记录开始时间）
        sync_record = SyncRecord.objects.create(
            device=device,
            start_time=start_time,
            file_count=file_count,
            end_time=timezone.now(), )

        sync_record.save()

    device.status = 'online'
    device.last_sync_time = timezone.now()
    device.save()

    return {
        'device_id': device.id,
        'status': device.status,
        'ip_address': device.ip_address,
        'sync_time': device.last_sync_time,
    }


@shared_task
def check_all_devices_status():
    """
    批量检查所有设备状态
    """
    for device in Device.objects.all():
        check_device_status.delay(device.id)


@shared_task
def sync_all_devices():
    """
    批量同步所有在线设备
    """
    for device in Device.objects.filter(status='online'):
        sync_device_files.delay(device.id)
