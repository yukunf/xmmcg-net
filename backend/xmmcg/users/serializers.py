from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


class UserRegistrationSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, data):
        """验证两次密码是否一致"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password': '两次输入的密码不一致'
            })
        
        # 验证用户名是否已存在
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({
                'username': '用户名已存在'
            })
        
        # 验证邮箱是否已存在
        if data.get('email') and User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({
                'email': '该邮箱已被注册'
            })
        
        return data

    def create(self, validated_data):
        """创建用户"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        fields = ('username', 'password')


class UserDetailSerializer(serializers.ModelSerializer):
    """用户详情序列化器（获取和修改用户信息）"""
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined')
        read_only_fields = ('id', 'username', 'date_joined')


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码序列化器"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        """验证新密码和确认密码是否一致"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password': '两次输入的新密码不一致'
            })
        return data
