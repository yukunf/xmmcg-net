from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    qqid = serializers.CharField(required=True, write_only=True)
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
        fields = ('username', 'qqid', 'email', 'password', 'password_confirm')
        extra_kwargs = {
            'email': {'required': True},
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
        #验证QQ号是否已存在
        if data.get('qqid') and UserProfile.objects.filter(qqid=data['qqid']).exists():
            raise serializers.ValidationError({
                'qqid': '该QQ号已被注册'
            })
        
        # 验证邮箱是否已存在
        if data.get('email') and User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({
                'email': '该邮箱已被注册'
            })
        
        return data

    def create(self, validated_data):
        """创建用户和用户资料"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        qqid = validated_data.pop('qqid', '') # User里没有qq号字段，以免出错
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        # 创建用户资料（包含 token）
        UserProfile.objects.create(user=user, qqid=qqid, token=0) # 已经获得了QQID。
        return user


class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        fields = ('username', 'password')


class UserDetailSerializer(serializers.ModelSerializer):
    """用户详情序列化器（获取和修改用户信息）"""
    token = serializers.SerializerMethodField()
    songsCount = serializers.SerializerMethodField()
    chartsCount = serializers.SerializerMethodField()
    qqid = serializers.CharField(source='profile.qqid', read_only=True)
    class Meta:
        model = User
        fields = ('username', 'qqid', 'email', 'is_active', 'date_joined', 'token', 'songsCount', 'chartsCount')
        read_only_fields = ('username', 'date_joined', 'token', 'songsCount', 'chartsCount')
    
    def get_token(self, obj):
        """获取用户代币，如果没有 profile 则创建一个"""
        try:
            return obj.profile.token
        except:
            # 如果没有 profile，创建一个
            from .models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=obj)
            return profile.token
    
    def get_songsCount(self, obj):
        """获取用户上传的歌曲数量"""
        return obj.songs.count()
    
    def get_chartsCount(self, obj):
        """获取用户上传的谱面数量"""
        return obj.charts.count() if hasattr(obj, 'charts') else 0


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


class UpdateTokenSerializer(serializers.Serializer):
    """修改用户 token 序列化器"""
    token = serializers.IntegerField(required=True, min_value=0)

    def validate_token(self, value):
        """验证 token 值"""
        if value < 0:
            raise serializers.ValidationError("Token 不能为负数")
        return value


class UserPublicSerializer(serializers.ModelSerializer):
    """
    专门用于公开展示的用户信息
    只包含：ID、用户名、QQ号、作品统计
    ❌ 绝对不包含：Token(余额)、Email、密码等
    """
    qqid = serializers.CharField(source='profile.qqid', read_only=True)
    songsCount = serializers.SerializerMethodField()
    chartsCount = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'qqid', 'songsCount', 'chartsCount')

    # 复用你之前的统计逻辑
    def get_songsCount(self, obj):
        return obj.songs.count()
    
    def get_chartsCount(self, obj):
        return obj.charts.count() if hasattr(obj, 'charts') else 0