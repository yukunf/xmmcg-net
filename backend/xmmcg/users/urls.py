from django.urls import path
from . import views

urlpatterns = [
    # CSRF token 获取
    path('csrf/', views.csrf_token_view, name='csrf_token'),

    # 认证相关
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    
    # 用户信息相关
    path('me/', views.get_current_user, name='get_current_user'),
    path('profile/', views.update_profile, name='update_profile'),
    path('<int:pk>/public/', views.get_user_public_info, name='get_user_public_info'),#专用获取其他用户可见信息
    
    # 密码管理
    path('change-password/', views.change_password, name='change_password'),
    
    # Token（虚拟货币）管理
    path('token/', views.get_user_token, name='get_user_token'),
    path('token/update/', views.update_user_token, name='update_user_token'),
    path('token/add/', views.add_user_token, name='add_user_token'),
    path('token/deduct/', views.deduct_user_token, name='deduct_user_token'),
    
    # 验证相关
    path('check-username/', views.check_username_availability, name='check_username_availability'),
    path('check-email/', views.check_email_availability, name='check_email_availability'),
    path('check-qqid/', views.check_qqid_availability, name='check_qqid_availability'),
]
