from django import forms
from .models import Device


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['ip_address', 'department', 'smb_username', 'smb_password',
                  'remote_path', 'local_path', 'remarks']
        widgets = {
            'smb_password': forms.PasswordInput(render_value=True),
            'remote_path': forms.TextInput(attrs={
                'placeholder': '例如：\\ip\\smb'
            }),
            'local_path': forms.TextInput(attrs={
                'placeholder': '例如：\\backup\\recordings'
            }),
            'remarks': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '可选备注信息'
            }),
        }
        labels = {
            'smb_username': 'SMB用户名',
            'smb_password': 'SMB密码',
            'remote_path': '远程共享路径',
            'local_path': '备份路径'
        }
