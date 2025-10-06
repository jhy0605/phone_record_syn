import urllib3
import urllib.parse
import json
import win32cred
import os
import shutil
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


def copy_file(file_path_a, file_path_b, device=None):
    from .models import Device  # 避免循环导入

    # 处理 device 参数（支持对象或 ID）
    if isinstance(device, int):
        device = Device.objects.get(id=device)
    elif device is not None and not isinstance(device, Device):
        raise ValueError("device 必须是 Device 实例或 ID")
    """
    改进版文件拷贝函数，带详细日志记录
    :param file_path_a: 源路径
    :param file_path_b: 目标路径
    :param device: 关联的设备对象(可选)
    :return: 成功拷贝的文件数量
    """
    n = 0
    temp_file_prefixes = ['~$', '.~', '~', '.tmp', 'temp']

    if not os.path.exists(file_path_a):
        error_msg = f"源路径不存在: {file_path_a}"
        SyncLog.objects.create(
            device=device,
            log_type='error',
            message=error_msg
        )
        return 0

    try:
        for root, dirs, files in os.walk(file_path_a):
            for file in files:
                # 跳过临时文件
                if any(file.startswith(prefix) for prefix in temp_file_prefixes):
                    continue

                filepath_a = os.path.join(root, file)
                filepath_b = filepath_a.replace(file_path_a, file_path_b)

                try:
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(filepath_b), exist_ok=True)

                    # 检查是否需要复制
                    if not os.path.exists(filepath_b) or os.path.getsize(filepath_a) != os.path.getsize(filepath_b):
                        shutil.copy2(filepath_a, filepath_b)

                        # 记录成功日志
                        success_msg = f"成功拷贝: {filepath_a} → {filepath_b}"
                        SyncLog.objects.create(
                            device=device,
                            log_type='info',
                            message=success_msg,
                            file_path=filepath_b
                        )
                        n += 1

                except Exception as e:
                    error_msg = f"拷贝失败 {filepath_a} → {filepath_b}: {str(e)}"
                    SyncLog.objects.create(
                        device=device,
                        log_type='error',
                        message=error_msg,
                        file_path=filepath_b
                    )

    except Exception as e:
        error_msg = f"同步过程中发生全局错误: {str(e)}"
        SyncLog.objects.create(
            device=device,
            log_type='error',
            message=error_msg
        )

    return n