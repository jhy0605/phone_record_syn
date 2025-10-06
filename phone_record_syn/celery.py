from __future__ import absolute_import
import os
from celery import Celery
from celery.schedules import crontab

# 设置默认Django settings模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'phone_record_syn.settings')

app = Celery('phone_record_syn')

# 使用Django的settings文件配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')


# 自动发现所有Django app中的tasks.py
app.autodiscover_tasks()

# 定时任务配置
app.conf.beat_schedule = {
    'check-devices-status': {
        'task': 'record_syn.tasks.check_all_devices_status',
        'schedule': 3600,
    },
    'sync-files-daily': {
        'task': 'record_syn.tasks.sync_all_devices',
        'schedule': crontab(hour=1, minute=0),
    }
}

# 查看 worker 状态（在项目目录下运行）
# celery -A phone_record_syn inspect registered | findstr "check_all_devices_status sync_files_task"

# 查看所有注册任务
# celery -A phone_record_syn inspect registered

# 查看已加载的定时任务
# celery -A phone_record_syn beat --loglevel=debug

# # 查看当前运行中的任务
# celery -A phone_record_syn inspect active

# 手动测试定时任务
# celery - A phone_record_syn call record_syn.tasks.check_all_devices_status

# 启动beat
# celery -A phone_record_syn beat --loglevel=info


