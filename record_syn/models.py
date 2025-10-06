from django.db import models
from django.utils import timezone


class Device(models.Model):
    """设备表"""
    STATUS_CHOICES = [
        ('online', '在线'),
        ('syncing', '同步中'),
        ('offline', '离线'),
    ]

    ip_address = models.CharField(max_length=15, verbose_name='IP地址')
    department = models.CharField(max_length=50, verbose_name='部门')
    smb_username = models.CharField(max_length=50, verbose_name='SMB用户名')  # 改名为smb_username更明确
    smb_password = models.CharField(max_length=100, verbose_name='SMB密码')  # 改名为smb_password
    remote_path = models.CharField(max_length=255, verbose_name='远程共享路径',
                                   help_text='格式：\\\\IP或主机名\\共享文件夹\\子目录')
    local_path = models.CharField(max_length=255, verbose_name='备份路径',
                                  help_text='格式：\\backup\\recordings')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='offline',
        verbose_name='状态'
    )
    last_sync_time = models.DateTimeField(
        verbose_name='最后同步时间',
        blank=True,
        null=True
    )
    remarks = models.TextField(verbose_name='备注', blank=True, null=True)

    class Meta:
        verbose_name = '设备'
        verbose_name_plural = '设备'

    def __str__(self):
        return f"{self.ip_address} ({self.department})"

    @property
    def unc_path(self):
        """生成标准UNC路径，兼容不同输入格式"""
        # 处理各种可能的输入格式
        path = self.remote_path.replace('/', '\\').strip('\\')
        return f"\\\\{self.ip_address}\\{path}"

    @property
    def normalized_local_path(self):
        """标准化本地路径，确保使用正确的路径分隔符"""
        import os
        return os.path.normpath(self.local_path)


class SyncRecord(models.Model):
    """同步记录表（通过外键关联获取设备信息）"""
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        verbose_name='设备',
        related_name='sync_records'  # 反向查询名称
    )
    start_time = models.DateTimeField(
        verbose_name='开始时间',
        default=timezone.now
    )
    end_time = models.DateTimeField(
        verbose_name='结束时间',
        blank=True,
        null=True
    )
    file_count = models.PositiveIntegerField(
        verbose_name='同步文件数量',
        default=0
    )

    class Meta:
        verbose_name = '同步记录'
        verbose_name_plural = '同步记录'
        ordering = ['-start_time']  # 按开始时间降序排列

    def __str__(self):
        return f"{self.device.ip_address} - {self.end_time:%Y-%m-%d %H:%M}"

    # 通过方法动态获取关联信息（非数据库字段）
    @property
    def ip_address(self):
        """动态获取设备IP（避免冗余存储）"""
        return self.device.ip_address

    @property
    def department(self):
        """动态获取设备部门（避免冗余存储）"""
        return self.device.department


class SyncLog(models.Model):
    LOG_TYPE_CHOICES = [
        ('info', '信息'),
        ('error', '错误'),
    ]

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='关联设备'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='时间戳'
    )
    log_type = models.CharField(
        max_length=10,
        choices=LOG_TYPE_CHOICES,
        verbose_name='日志类型'
    )
    message = models.TextField(verbose_name='日志消息')
    file_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='文件路径'
    )

    class Meta:
        verbose_name = '同步日志'
        verbose_name_plural = '同步日志'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.get_log_type_display()}] {self.timestamp}: {self.message[:50]}"
