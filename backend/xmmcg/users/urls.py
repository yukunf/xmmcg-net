from django.urls import path
from . import views

urlpatterns = [
    # 认证相关
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    
    # 用户信息相关
    path('me/', views.get_current_user, name='get_current_user'),
    path('profile/', views.update_profile, name='update_profile'),
    
    # 密码管理
    path('change-password/', views.change_password, name='change_password'),
    
    # 验证相关
    path('check-username/', views.check_username_availability, name='check_username_availability'),
    path('check-email/', views.check_email_availability, name='check_email_availability'),
]
