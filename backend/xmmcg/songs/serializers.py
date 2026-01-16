from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Song
from .utils import (
    calculate_file_hash,
    validate_audio_file,
    validate_cover_image,
    validate_title
)


class SongUserSerializer(serializers.ModelSerializer):
    """歌曲所属用户的简介信息"""
    
    class Meta:
        model = User
        fields = ('id', 'username')


class SongUploadSerializer(serializers.ModelSerializer):
    """歌曲上传序列化器"""
    
    class Meta:
        model = Song
        fields = ('title', 'audio_file', 'cover_image', 'netease_url')
        extra_kwargs = {
            'title': {'required': True},
            'audio_file': {'required': True},
            'cover_image': {'required': False},
            'netease_url': {'required': False},
        }
    
    def validate_title(self, value):
        """验证标题"""
        is_valid, error_msg = validate_title(value)
        if not is_valid:
            raise serializers.ValidationError(error_msg)
        return value
    
    def validate_audio_file(self, value):
        """验证音频文件"""
        is_valid, error_msg = validate_audio_file(value)
        if not is_valid:
            raise serializers.ValidationError(error_msg)
        return value
    
    def validate_cover_image(self, value):
        """验证封面图片"""
        if value:  # 封面是可选的
            is_valid, error_msg = validate_cover_image(value)
            if not is_valid:
                raise serializers.ValidationError(error_msg)
        return value
    
    def create(self, validated_data):
        """创建歌曲"""
        user = self.context['request'].user
        audio_file = validated_data['audio_file']
        
        # 计算音频文件哈希
        audio_hash = calculate_file_hash(audio_file)
        
        song = Song.objects.create(
            user=user,
            audio_hash=audio_hash,
            file_size=audio_file.size,
            **validated_data
        )
        return song


class SongDetailSerializer(serializers.ModelSerializer):
    """歌曲详情序列化器（返回完整信息）"""
    user = SongUserSerializer(read_only=True)
    audio_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Song
        fields = (
            'id',
            'title',
            'user',
            'audio_url',
            'cover_url',
            'netease_url',
            'file_size',
            'created_at',
            'updated_at'
        )
        read_only_fields = ('id', 'user', 'file_size', 'created_at', 'updated_at')
    
    def get_audio_url(self, obj):
        """获取音频文件 URL"""
        if obj.audio_file:
            return obj.audio_file.url
        return None
    
    def get_cover_url(self, obj):
        """获取封面文件 URL"""
        if obj.cover_image:
            return obj.cover_image.url
        return None


class SongListSerializer(serializers.ModelSerializer):
    """歌曲列表序列化器（返回精简信息）"""
    user = SongUserSerializer(read_only=True)
    cover_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Song
        fields = (
            'id',
            'title',
            'user',
            'cover_url',
            'file_size',
            'created_at'
        )
        read_only_fields = fields
    
    def get_cover_url(self, obj):
        """获取封面文件 URL"""
        if obj.cover_image:
            return obj.cover_image.url
        return None


class SongUpdateSerializer(serializers.ModelSerializer):
    """歌曲更新序列化器（仅允许更新非文件字段）"""
    
    class Meta:
        model = Song
        fields = ('title', 'netease_url')
    
    def validate_title(self, value):
        """验证标题"""
        is_valid, error_msg = validate_title(value)
        if not is_valid:
            raise serializers.ValidationError(error_msg)
        return value


# ==================== 竞标相关序列化器 ====================

from .models import Bid, BidResult, BiddingRound


class BiddingRoundSerializer(serializers.ModelSerializer):
    """竞标轮次序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = BiddingRound
        fields = ('id', 'name', 'status', 'status_display', 'created_at', 'started_at', 'completed_at')
        read_only_fields = ('id', 'created_at')


class BidSerializer(serializers.ModelSerializer):
    """竞标序列化器"""
    song = SongListSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Bid
        fields = ('id', 'username', 'song', 'amount', 'is_dropped', 'created_at')
        read_only_fields = ('id', 'username', 'is_dropped', 'created_at')


class BidResultSerializer(serializers.ModelSerializer):
    """竞标结果序列化器"""
    song = SongListSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    allocation_type_display = serializers.CharField(source='get_allocation_type_display', read_only=True)
    
    class Meta:
        model = BidResult
        fields = ('id', 'username', 'song', 'bid_amount', 'allocation_type', 'allocation_type_display', 'allocated_at')
        read_only_fields = ('id', 'username', 'allocated_at')
