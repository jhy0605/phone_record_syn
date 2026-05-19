import urllib3
import urllib.parse
import json
import win32cred
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from .models import SyncLog  # 假设您已创建SyncLog模型


def call_api(phone_number):
    host = 'https://kzempty.market.alicloudapi.com'
    path = '/api-mall/api/mobile_empty/check'
    appcode = '395a1e1794434d25b9a3b735126d4527'
    url = host + path

    http = urllib3.PoolManager()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Authorization': 'APPCODE ' + appcode
    }
    bodys = {'mobile': phone_number}
    post_data = urllib.parse.urlencode(bodys).encode('utf-8')
    response = http.request('POST', url, body=post_data, headers=headers)
    content = response.data.decode('utf-8')

    return json.loads(content) if content else None


def add_credentials(data_list):
    for data in data_list:
        # 准备凭证信息
        credential = {
            'TargetName': data['ip'],
            'Type': win32cred.CRED_TYPE_DOMAIN_PASSWORD,
            'UserName': data['user'].replace('\\\\', '\\'),
            'CredentialBlob': data['passwd'],
            'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE  # 或者使用 win32cred.CRED_PERSIST_ENTERPRISE，根据需要选择
        }
        win32cred.CredWrite(credential, 0)
        print('凭据添加成功')


# 线程安全的日志缓冲区和计数器
logs_buffer_lock = Lock()
copy_count_lock = Lock()


def _copy_single_file(args):
    """
    单个文件拷贝函数（用于多线程）
    :param args: (filepath_a, filepath_b, device_id) 元组
    :return: (success, log_dict_or_none, error_dict_or_none) 元组
              返回字典而非 Django 对象，避免线程安全问题
    """
    filepath_a, filepath_b, device_id = args
    
    try:
        # 确保目标目录存在
        os.makedirs(os.path.dirname(filepath_b), exist_ok=True)

        # 获取源文件信息
        src_stat = os.stat(filepath_a)
        src_size = src_stat.st_size
        src_mtime = src_stat.st_mtime

        # 检查是否需要复制
        need_copy = False
        if not os.path.exists(filepath_b):
            need_copy = True
        else:
            dst_stat = os.stat(filepath_b)
            dst_size = dst_stat.st_size
            dst_mtime = dst_stat.st_mtime
            
            if src_mtime != dst_mtime or src_size != dst_size:
                need_copy = True

        if need_copy:
            shutil.copy2(filepath_a, filepath_b)
            
            # 记录成功日志（返回字典，避免 Django 对象线程安全问题）
            success_msg = f"成功拷贝: {filepath_a} → {filepath_b}"
            log_dict = {
                'device_id': device_id,
                'log_type': 'info',
                'message': success_msg,
                'file_path': filepath_b
            }
            return (True, log_dict, None)
        else:
            return (False, None, None)
            
    except Exception as e:
        error_msg = f"拷贝失败 {filepath_a} → {filepath_b}: {str(e)}"
        error_dict = {
            'device_id': device_id,
            'log_type': 'error',
            'message': error_msg,
            'file_path': filepath_b
        }
        return (False, None, error_dict)


def copy_file(file_path_a, file_path_b, device=None, max_workers=8):
    from .models import Device  # 避免循环导入

    # 处理 device 参数（支持对象或 ID）
    if isinstance(device, int):
        device = Device.objects.get(id=device)
    elif device is not None and not isinstance(device, Device):
        raise ValueError("device 必须是 Device 实例或 ID")
    """
    多线程并行文件拷贝函数，使用修改时间快速筛选 + 批量日志写入
    :param file_path_a: 源路径
    :param file_path_b: 目标路径
    :param device: 关联的设备对象(可选)
    :param max_workers: 最大线程数（默认8）
    :return: 成功拷贝的文件数量
    """
    n = 0
    temp_file_prefixes = ['~$', '.~', '~', '.tmp', 'temp']
    logs_buffer = []  # 日志缓冲区

    if not os.path.exists(file_path_a):
        error_msg = f"源路径不存在: {file_path_a}"
        SyncLog.objects.create(
            device=device,
            log_type='error',
            message=error_msg
        )
        return 0

    try:
        # 第一阶段：扫描所有需要拷贝的文件
        files_to_copy = []
        for root, dirs, files in os.walk(file_path_a):
            for file in files:
                # 跳过临时文件
                if any(file.startswith(prefix) for prefix in temp_file_prefixes):
                    continue

                filepath_a = os.path.join(root, file)
                # 使用相对路径计算，避免 replace 的潜在问题
                relative_path = os.path.relpath(filepath_a, file_path_a)
                filepath_b = os.path.join(file_path_b, relative_path)
                files_to_copy.append((filepath_a, filepath_b, device.id))

        # 第二阶段：多线程并行拷贝
        if files_to_copy:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_file = {
                    executor.submit(_copy_single_file, args): args 
                    for args in files_to_copy
                }
                
                # 处理完成的任务
                for future in as_completed(future_to_file):
                    success, log_dict, error_dict = future.result()
                    
                    if success:
                        n += 1
                        if log_dict:
                            # 将字典转换为 Django 对象
                            logs_buffer.append(SyncLog(**log_dict))
                            
                            # 每 100 条日志批量插入一次
                            if len(logs_buffer) >= 100:
                                with logs_buffer_lock:
                                    SyncLog.objects.bulk_create(logs_buffer)
                                    logs_buffer.clear()
                    
                    # 错误日志立即写入
                    if error_dict:
                        SyncLog.objects.create(**error_dict)

        # 同步完成后，写入剩余的日志
        if logs_buffer:
            with logs_buffer_lock:
                SyncLog.objects.bulk_create(logs_buffer)
                logs_buffer.clear()

    except Exception as e:
        error_msg = f"同步过程中发生全局错误: {str(e)}"
        SyncLog.objects.create(
            device=device,
            log_type='error',
            message=error_msg
        )

    return n