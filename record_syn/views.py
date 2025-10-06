from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Device, SyncRecord, SyncLog
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from datetime import timedelta
from django.db import models  # 添加这行
from django.db.models import Count, Q  # 同时确保这些导入存在
from .forms import DeviceForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.db.models import Sum, DateField
from collections import defaultdict


# 用户登录视图
def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'欢迎回来, {user.username}!')
            next_url = request.POST.get('next', 'home')  # 获取next参数或默认值
            return redirect(next_url)
    else:
        next_url = request.GET.get('next', 'home')
        form = AuthenticationForm()
    return render(request, 'record_syn/login.html', {
        'form': form,
        'next': next_url
    })


# 用户注销视图
def logout(request):
    auth_logout(request)  # 注销用户
    messages.success(request, '您已注销.')
    return redirect('login')  # 注销成功后重定向到登录页面


@login_required
def device_list(request):
    """设备列表页"""
    today = timezone.now().date()
    current_month = today.month

    # 获取所有设备并按最后同步时间降序排列
    devices = Device.objects.annotate(
        current_month_syncs=Count(
            'sync_records',
            filter=models.Q(sync_records__start_time__month=current_month)
        )
    ).order_by('-last_sync_time')  # 修改排序字段为 last_sync_time

    # 搜索参数
    query = request.GET.get('q')  # 设备名称/IP/部门搜索
    status = request.GET.get('status')  # 状态过滤

    # 搜索过滤
    if query:
        devices = devices.filter(
            models.Q(ip_address__icontains=query) |
            models.Q(department__icontains=query) |
            models.Q(remarks__icontains=query)
        )
    if status:
        devices = devices.filter(status=status)

    # 分页
    paginator = Paginator(devices, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'record_syn/device_list.html', {
        'page_obj': page_obj,
        'status_choices': Device.STATUS_CHOICES,
        'current_month': current_month  # 传递当前月份到模板
    })


@login_required
def home(request):
    """新版主页-同步数据统计"""
    now = timezone.now()
    today = now.date()
    first_day_of_month = today.replace(day=1)
    end_date = today
    start_date = end_date - timedelta(days=29)  # 30天趋势的开始日期

    # 1. 本月总文件数 (改进版)
    monthly_stats = SyncRecord.objects.filter(
        start_time__gte=first_day_of_month
    ).aggregate(
        monthly_total=Coalesce(Sum('file_count'), 0)
    )

    # 2. 今日文件数 (改进版)
    today_stats = SyncRecord.objects.filter(
        start_time__gte=today,
        start_time__lt=today + timedelta(days=1)
    ).aggregate(
        today_total=Coalesce(Sum('file_count'), 0)
    )

    # 3. 活跃设备数 (改进版)
    active_device_count = (
        SyncRecord.objects
        .filter(start_time__gte=now - timedelta(days=30))
        .values('device')
        .distinct()
        .count()
    )

    # 4. 设备文件数量排名（保持原逻辑）
    device_ranking = (
        Device.objects
        .annotate(total_files=Sum('sync_records__file_count'))
        .order_by('-total_files')[:5]
    )

    # 5. 设备状态统计（保持原逻辑）
    device_status_counts = Device.objects.aggregate(
        online=Count('id', filter=Q(status='online')),
        syncing=Count('id', filter=Q(status='syncing')),
        offline=Count('id', filter=Q(status='offline'))
    )

    # 6. 最近同步记录（保持原逻辑）
    recent_sync_records = (
        SyncRecord.objects
        .select_related('device')
        .order_by('-start_time')[:11]
    )

    # 7. 30天趋势数据（保持原逻辑）
    stats_dict = defaultdict(int)

    for record in SyncRecord.objects.filter(
            start_time__range=(start_date, end_date)
    ).values('start_time', 'file_count'):
        date_key = record['start_time'].date()
        stats_dict[date_key] += record['file_count']

    # 转换为普通字典
    stats_dict = dict(stats_dict)

    print('最终数据：', stats_dict)

    return render(request, 'record_syn/home.html', {
        'monthly_total': monthly_stats['monthly_total'] or 0,
        'today_total': today_stats['today_total'] or 0,
        'active_device_count': active_device_count,
        'device_ranking': device_ranking,
        'online_devices': device_status_counts['online'],
        'syncing_devices': device_status_counts['syncing'],
        'offline_devices': device_status_counts['offline'],
        'recent_sync_records': recent_sync_records,
        'daily_stats': stats_dict,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def add_device(request):
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '设备添加成功')
            return redirect('device_list')
    else:
        form = DeviceForm()

    return render(request, 'record_syn/add_device.html', {'form': form})


# 重新连接按钮：触发 reconnect_device 视图，调用异步任务
@login_required
def reconnect_device(request, pk):
    print(f"收到设备 {pk} 的重连请求")  # 确认请求是否到达
    from .tasks import check_device_status
    check_device_status.delay(pk)
    return JsonResponse({'status': 'success'})


@login_required
def sync_device(request, pk):
    from .tasks import sync_device_files
    try:
        result = sync_device_files.delay(pk)
        return JsonResponse({
            'status': 'pending',
            'message': '同步任务已启动，请稍后刷新查看结果'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'启动同步任务失败: {str(e)}'
        })


@login_required
def edit_device(request, pk):
    device = Device.objects.get(id=pk)
    if request.method == 'POST':
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            device = form.save(commit=False)
            device.status = 'offline'  # 强制设置为离线状态
            device.save()
            messages.success(request, '设备信息已更新，状态已设为离线')
            return redirect('device_list')
    else:
        form = DeviceForm(instance=device)
    return render(request, 'record_syn/edit_device.html', {'form': form})


@login_required
def delete_device(request, pk):
    device = get_object_or_404(Device, id=pk)
    if request.method == 'POST':
        try:
            device.delete()
            return JsonResponse({'status': 'success'}, status=200)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)


@login_required
def sync_records(request):
    # 获取查询参数
    search_query = request.GET.get('q', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # 基础查询
    records = SyncRecord.objects.select_related('device').order_by('-start_time')

    # 应用搜索过滤
    if search_query:
        records = records.filter(
            Q(device__ip_address__icontains=search_query) |
            Q(device__department__icontains=search_query)
        )

    # 应用日期范围过滤
    if start_date:
        records = records.filter(start_time__date__gte=start_date)
    if end_date:
        records = records.filter(start_time__date__lte=end_date)

    # 分页
    paginator = Paginator(records, 25)
    page = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'record_syn/sync_records.html', {
        'recent_records': page_obj,
        'search_query': search_query,
        'start_date': start_date if 'start_date' in locals() else '',
        'end_date': end_date if 'end_date' in locals() else '',
    })
