from django.contrib import admin
from django import forms
from .models import Device, SyncRecord, SyncLog
from django.utils.html import format_html
from datetime import datetime, timedelta


class DateRangeFilter(admin.SimpleListFilter):
    title = '时间范围'
    parameter_name = 'daterange'

    def lookups(self, request, model_admin):
        return (
            ('today', '今天'),
            ('yesterday', '昨天'),
            ('week', '本周'),
            ('month', '本月'),
            ('custom', '自定义'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'today':
            return queryset.filter(timestamp__date=datetime.today())
        elif self.value() == 'yesterday':
            return queryset.filter(timestamp__date=datetime.today() - timedelta(days=1))
        elif self.value() == 'week':
            return queryset.filter(timestamp__gte=datetime.today() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(timestamp__gte=datetime.today() - timedelta(days=30))
        elif self.value() == 'custom':
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            if start_date and end_date:
                return queryset.filter(
                    timestamp__gte=datetime.strptime(start_date, '%Y-%m-%d'),
                    timestamp__lte=datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                )
        return queryset


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('formatted_timestamp', 'device_link', 'log_type_display', 'full_message')
    list_filter = (
        ('timestamp', admin.DateFieldListFilter),  # 使用内置日期筛选
        'log_type',
        'device'
    )
    # 新增搜索字段配置
    search_fields = ['message', 'device__ip_address', 'log_type']

    # 补充时间格式化方法
    def formatted_timestamp(self, obj):
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S')

    formatted_timestamp.short_description = '时间'
    formatted_timestamp.admin_order_field = 'timestamp'

    # 优化后的设备链接
    def device_link(self, obj):
        if obj.device:
            # 使用原始URL格式（不推荐但简单）
            return format_html(
                '<a href="{}">{}</a>',
                f'/admin/record_syn/device/{obj.device.id}/change/',
                obj.device.ip_address
            )
        return '-'

    device_link.short_description = '设备'

    # 日志类型显示
    def log_type_display(self, obj):
        color = 'green' if obj.log_type == 'info' else 'red'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_log_type_display()
        )

    log_type_display.short_description = '类型'

    # 完整消息显示
    def full_message(self, obj):
        return format_html(
            '<div style="max-width: 800px; overflow-wrap: break-word;">{}</div>',
            obj.message
        )

    full_message.short_description = '消息详情'
