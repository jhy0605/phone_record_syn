from django.apps import AppConfig


class RecordSynConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'record_syn'
    verbose_name = '录音同步'  # 中文显示名称
