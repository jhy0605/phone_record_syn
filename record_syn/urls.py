from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView
from .views import home, login

from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path('home/', views.home, name='home'),  # 主页
    path('devices/', views.device_list, name='device_list'),  # 设备列表
    path('devices/add/', views.add_device, name='add_device'),  # 添加设备
    path('api/devices/<int:pk>/reconnect/', views.reconnect_device, name='reconnect_device'),  # 重连设备
    path('api/devices/<int:pk>/sync/', views.sync_device, name='sync_device'),  # 同步设备
    path('devices/<int:pk>/edit/', views.edit_device, name='edit_device'),  # 编辑设备
    path('devices/<int:pk>/delete/', views.delete_device, name='delete_device'),  # 删除设备
    path('sync-records/', views.sync_records, name='sync_records'),
    path('login/', LoginView.as_view(
        template_name='record_syn/login.html',
        extra_context={'next': 'home'}  # 明确指定next参数
    ), name='login'),  # 登录
    path('logout/', views.logout, name='logout'),
]
