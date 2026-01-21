from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.middleware.csrf import get_token

from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserDetailSerializer,
    ChangePasswordSerializer,
    UpdateTokenSerializer,
)
from .models import UserProfile


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    用户注册
    POST: 注册新用户
    """
    if request.method == 'POST':
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'success': True,
                'message': '注册成功',
                'user': UserDetailSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    用户登录
    POST: 用户名和密码登录
    """
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # 使用 Django session 认证
            from django.contrib.auth import login as auth_login
            auth_login(request, user)
            
            return Response({
                'success': True,
                'message': '登录成功',
                'user': UserDetailSerializer(user).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': '用户名或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    用户登出
    POST: 清除用户会话
    """
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    return Response({
        'success': True,
        'message': '登出成功'
    }, status=status.HTTP_200_OK)

from .serializers import UserPublicSerializer 

@api_view(['GET'])
@permission_classes([IsAuthenticated]) # 或者 AllowAny，看你想不想让游客看
def get_user_public_info(request, pk):
    """
    根据用户ID获取公开信息
    API: GET /users/<int:pk>/public/
    """
    # 查找指定ID的用户，找不到返回 404
    target_user = get_object_or_404(User, pk=pk)
    
    serializer = UserPublicSerializer(target_user)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    获取当前登录用户的信息
    GET: 返回当前用户信息
    """
    user = request.user
    serializer = UserDetailSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_token_view(request):
    """返回并设置 CSRF Token，供前端获取。"""
    token = get_token(request)
    return Response({'csrfToken': token}, status=status.HTTP_200_OK)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    修改用户个人信息（邮箱等）
    PUT/PATCH: 修改用户信息
    只支持修改 email 字段
    """
    user = request.user
    
    # 只允许修改 email
    allowed_fields = {'email'}
    provided_fields = set(request.data.keys())
    invalid_fields = provided_fields - allowed_fields
    
    if invalid_fields:
        return Response({
            'success': False,
            'message': f'不允许修改字段: {", ".join(invalid_fields)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = UserDetailSerializer(user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': '个人信息已更新',
            'user': serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    修改密码
    POST: 
        old_password: 旧密码
        new_password: 新密码
        new_password_confirm: 确认新密码
    """
    user = request.user
    serializer = ChangePasswordSerializer(data=request.data)
    
    if serializer.is_valid():
        # 验证旧密码
        old_password = serializer.validated_data['old_password']
        if not user.check_password(old_password):
            return Response({
                'success': False,
                'message': '旧密码错误'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 设置新密码
        new_password = serializer.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        
        return Response({
            'success': True,
            'message': '密码已更改'
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_username_availability(request):
    """
    检查用户名是否可用
    POST: 
        username: 要检查的用户名
    """
    username = request.data.get('username', '').strip()
    
    if not username:
        return Response({
            'success': False,
            'message': '用户名不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    exists = User.objects.filter(username=username).exists()
    return Response({
        'success': True,
        'available': not exists,
        'username': username
    }, status=status.HTTP_200_OK)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def check_qqid_availability(request):
    """
    检查QQ号是否可用
    POST: 
        qqid: 要检查的QQ号
    """
    qqid = request.data.get('qqid', '').strip()
    
    if not qqid:
        return Response({
            'success': False,
            'message': 'QQ号不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    exists = UserProfile.objects.filter(qqid=qqid).exists()
    return Response({
        'success': True,
        'available': not exists,
        'qqid': qqid
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_email_availability(request):
    """
    检查邮箱是否可用
    POST:
        email: 要检查的邮箱
    """
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response({
            'success': False,
            'message': '邮箱不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    exists = User.objects.filter(email__iexact=email).exists()
    return Response({
        'success': True,
        'available': not exists,
        'email': email
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_token(request):
    """
    获取当前用户的 token（虚拟货币）余额
    GET: 返回用户的 token 余额
    """
    user = request.user
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user, token=0)
    
    return Response({
        'success': True,
        'user_id': user.id,
        'username': user.username,
        'token': profile.token
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user_token(request):
    """
    修改用户的 token（虚拟货币）余额
    POST:
        token: 新的 token 值（必须是非负整数）
    
    注：此操作通常由网站内部逻辑调用，前端应谨慎调用此端点
    """
    user = request.user
    serializer = UpdateTokenSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=user, token=0)
        
        new_token = serializer.validated_data['token']
        old_token = profile.token
        profile.token = new_token
        profile.save()
        
        return Response({
            'success': True,
            'message': 'Token 已更新',
            'user_id': user.id,
            'username': user.username,
            'old_token': old_token,
            'new_token': new_token
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_user_token(request):
    """
    增加用户的 token（虚拟货币）
    POST:
        amount: 增加的 token 数量（必须是正整数）
    
    例：
    - {"amount": 100} 增加 100 token
    """
    user = request.user
    
    try:
        amount = int(request.data.get('amount', 0))
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'message': 'amount 必须是整数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if amount < 0:
        return Response({
            'success': False,
            'message': '增加数量必须为正数，如需扣除请使用 /token/deduct/ 端点'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user, token=0)
    
    old_token = profile.token
    new_token = old_token + amount
    profile.token = new_token
    profile.save()
    
    return Response({
        'success': True,
        'message': f'Token 已增加 {amount}',
        'user_id': user.id,
        'username': user.username,
        'old_token': old_token,
        'new_token': new_token,
        'amount_changed': amount
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deduct_user_token(request):
    """
    扣除用户的 token（虚拟货币）
    POST:
        amount: 扣除的 token 数量（必须是正整数）
    
    例：
    - {"amount": 50} 扣除 50 token
    
    错误：
    - 如果 token 余额不足，返回 400 错误
    """
    user = request.user
    
    try:
        amount = int(request.data.get('amount', 0))
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'message': 'amount 必须是整数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if amount < 0:
        return Response({
            'success': False,
            'message': '扣除数量必须为正数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if amount == 0:
        return Response({
            'success': False,
            'message': '扣除数量必须大于 0'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user, token=0)
    
    old_token = profile.token
    new_token = old_token - amount
    
    # 防止 token 变成负数
    if new_token < 0:
        return Response({
            'success': False,
            'message': f'Token 余额不足。当前余额: {old_token}，无法扣除 {amount}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    profile.token = new_token
    profile.save()
    
    return Response({
        'success': True,
        'message': f'Token 已扣除 {amount}',
        'user_id': user.id,
        'username': user.username,
        'old_token': old_token,
        'new_token': new_token,
        'amount_changed': -amount
    }, status=status.HTTP_200_OK)

