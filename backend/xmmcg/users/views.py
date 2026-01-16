from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserDetailSerializer,
    ChangePasswordSerializer,
)


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    获取当前登录用户的信息
    GET: 返回当前用户信息
    """
    user = request.user
    serializer = UserDetailSerializer(user)
    return Response({
        'success': True,
        'user': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    修改用户个人信息（邮箱、名字等）
    PUT/PATCH: 修改用户信息
    """
    user = request.user
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
