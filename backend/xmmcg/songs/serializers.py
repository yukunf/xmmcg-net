import re
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Song, Banner, Announcement, CompetitionPhase
from .utils import (
    calculate_file_hash,
    validate_audio_file,
    validate_cover_image,
    validate_background_video,
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
        fields = ('title', 'audio_file', 'cover_image', 'background_video', 'netease_url')
        extra_kwargs = {
            'title': {'required': True},
            'audio_file': {'required': True},
            'cover_image': {'required': False},
            'background_video': {'required': False},
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
    
    def validate_background_video(self, value):
        """验证背景视频"""
        is_valid, error_msg = validate_background_video(value)
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
    video_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Song
        fields = (
            'id',
            'title',
            'user',
            'audio_url',
            'cover_url',
            'video_url',
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

    def get_video_url(self, obj):
        """获取背景视频文件 URL"""
        if obj.background_video:
            return obj.background_video.url
        return None


class SongListSerializer(serializers.ModelSerializer):
    """歌曲列表序列化器（返回精简信息）"""
    user = SongUserSerializer(read_only=True)
    audio_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Song
        fields = (
            'id',
            'title',
            'user',
            'audio_url',
            'cover_url',
            'video_url',
            'netease_url',
            'file_size',
            'created_at'
        )
        read_only_fields = fields
    
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
    
    def get_video_url(self, obj):
        """获取背景视频文件 URL"""
        if obj.background_video:
            return obj.background_video.url
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
    """竞标序列化器（支持歌曲和谱面）"""
    song = SongListSerializer(read_only=True)
    chart = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    status = serializers.SerializerMethodField()
    bid_type_display = serializers.CharField(source='get_bid_type_display', read_only=True)
    
    class Meta:
        model = Bid
        fields = ('id', 'username', 'bid_type', 'bid_type_display', 'song', 'chart', 'amount', 'is_dropped', 'status', 'created_at')
        read_only_fields = ('id', 'username', 'is_dropped', 'created_at')
    
    def get_chart(self, obj):
        """获取谱面信息（仅当bid_type=chart时）"""
        if obj.chart:
            return {
                'id': obj.chart.id,
                'song': {
                    'id': obj.chart.song.id,
                    'title': obj.chart.song.title
                },
                'creator_username': obj.chart.user.username,
                'average_score': obj.chart.average_score,
                'created_at': obj.chart.created_at
            }
        return None
    
    def get_status(self, obj):
        """
        获取竞标状态
        - bidding: 进行中
        - won: 已中选
        - lost: 已落选
        """
        from .models import BidResult
        
        # 检查竞标轮次是否已完成
        if obj.bidding_round.status != 'completed':
            return 'bidding'
        
        # 检查是否中选
        result = BidResult.objects.filter(
            bidding_round=obj.bidding_round,
            user=obj.user
        ).first()
        
        if result:
            # 检查是否是这个竞标对应的目标（歌曲或谱面）
            if obj.bid_type == 'song' and result.song_id == obj.song_id:
                return 'won'
            elif obj.bid_type == 'chart' and result.chart_id == obj.chart_id:
                return 'won'
        
        return 'lost'


class BidResultSerializer(serializers.ModelSerializer):
    """竞标结果序列化器（支持歌曲和谱面）"""
    song = SongListSerializer(read_only=True)
    chart = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    allocation_type_display = serializers.CharField(source='get_allocation_type_display', read_only=True)
    bid_type_display = serializers.CharField(source='get_bid_type_display', read_only=True)
    
    class Meta:
        model = BidResult
        fields = (
            'id', 'username', 'bid_type', 'bid_type_display', 'song', 'chart',
            'bid_amount', 'allocation_type', 'allocation_type_display', 'allocated_at'
        )
        read_only_fields = fields
    
    def get_chart(self, obj):
        """获取谱面信息（仅当bid_type=chart时）"""
        if obj.chart:
            return {
                'id': obj.chart.id,
                'song': {
                    'id': obj.chart.song.id,
                    'title': obj.chart.song.title
                },
                'creator_username': obj.chart.user.username,
                'average_score': obj.chart.average_score,
                'created_at': obj.chart.created_at
            }
        return None


# ==================== 谱面和互评相关序列化器 ====================

from .models import Chart, PeerReview, PeerReviewAllocation


class ChartSerializer(serializers.ModelSerializer):
    """谱面序列化器"""
    song = SongListSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    chart_file_url = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    designer = serializers.CharField(read_only=True)
    part_one_chart = serializers.SerializerMethodField()
    completion_bid_result = serializers.SerializerMethodField()
    
    class Meta:
        model = Chart
        fields = (
            'id', 'username', 'song', 'status', 'status_display', 'designer',
            'audio_file', 'audio_url', 'cover_image', 'cover_url', 'background_video', 'video_url', 'chart_file', 'chart_file_url',
            'review_count', 'average_score', 'created_at', 'submitted_at', 'review_completed_at',
            'is_part_one', 'part_one_chart', 'completion_bid_result'
        )
        read_only_fields = (
            'id', 'username', 'review_count', 'average_score',
            'created_at', 'submitted_at', 'review_completed_at'
        )
    
    def _build_url(self, request, field):
        if field:
            return request.build_absolute_uri(field.url) if request else field.url
        return None

    def get_chart_file_url(self, obj):
        """获取谱面文件的完整URL"""
        request = self.context.get('request')
        return self._build_url(request, obj.chart_file)

    def get_audio_url(self, obj):
        """获取音频文件URL"""
        request = self.context.get('request')
        return self._build_url(request, obj.audio_file)

    def get_cover_url(self, obj):
        """获取封面文件URL"""
        request = self.context.get('request')
        return self._build_url(request, obj.cover_image)

    def get_video_url(self, obj):
        """获取背景视频文件URL"""
        request = self.context.get('request')
        return self._build_url(request, obj.background_video)

    def get_part_one_chart(self, obj):
        """获取第一部分谱面信息"""
        if obj.part_one_chart:
            return {
                'id': obj.part_one_chart.id,
                'designer': obj.part_one_chart.designer,
                'status': obj.part_one_chart.status
            }
        return None

    def get_completion_bid_result(self, obj):
        """获取完成竞标结果信息"""
        if obj.completion_bid_result:
            return {
                'id': obj.completion_bid_result.id,
                'bid_amount': obj.completion_bid_result.bid_amount,
                'bid_type': obj.completion_bid_result.bid_type
            }
        return None


class ChartCreateSerializer(serializers.ModelSerializer):
    """谱面创建序列化器"""
    
    class Meta:
        model = Chart
        fields = ('designer', 'audio_file', 'cover_image', 'background_video', 'chart_file')
        extra_kwargs = {
            'designer': {'required': False},  # 从谱面文件解析
            'audio_file': {'required': True},
            'cover_image': {'required': True},
            'background_video': {'required': False},
            'chart_file': {'required': True},
        }
    
    def validate_chart_file(self, value):
        """验证谱面文件"""
        # 验证文件名必须是maidata.txt
        if value.name != 'maidata.txt':
            raise serializers.ValidationError('谱面文件必须命名为 maidata.txt')
        
        # 验证文件大小（例如限制为1MB）
        if value.size > 1 * 1024 * 1024:
            raise serializers.ValidationError('谱面文件大小不能超过 1MB')
        
        return value

    def validate_audio_file(self, value):
        """验证音频文件（沿用歌曲校验规则）"""
        is_valid, error_msg = validate_audio_file(value)
        if not is_valid:
            raise serializers.ValidationError(error_msg)
        return value

    def validate_cover_image(self, value):
        """验证封面图片"""
        is_valid, error_msg = validate_cover_image(value)
        if not is_valid:
            raise serializers.ValidationError(error_msg)
        return value

    def validate_background_video(self, value):
        """验证背景视频"""
        if value:  # 可选
            is_valid, error_msg = validate_background_video(value)
            if not is_valid:
                raise serializers.ValidationError(error_msg)
        return value

    def validate(self, attrs):
        chart_file = attrs.get('chart_file')
        if chart_file:
            content = chart_file.read().decode('utf-8', errors='ignore')
            match = re.search(r'^\s*&des=(.+)$', content, re.MULTILINE)
            chart_file.seek(0)
            if not match or not match.group(1).strip():
                raise serializers.ValidationError({'chart_file': '请填写谱师名义'})
            attrs['designer'] = match.group(1).strip()
        else:
            raise serializers.ValidationError({'chart_file': '谱面文件不能为空'})
        return attrs


class PeerReviewAllocationSerializer(serializers.ModelSerializer):
    """互评任务序列化器（用于获取待评分任务）"""
    chart_id = serializers.IntegerField(source='chart.id', read_only=True)
    song_title = serializers.CharField(source='chart.song.title', read_only=True)
    chart_designer = serializers.CharField(source='chart.designer', read_only=True)
    chart_file_url = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PeerReviewAllocation
        fields = (
            'id', 'chart_id', 'song_title', 'chart_designer', 'chart_file_url',
            'status', 'status_display', 'allocated_at'
        )
        read_only_fields = fields
    
    def get_chart_file_url(self, obj):
        """获取谱面文件的完整URL"""
        if obj.chart.chart_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.chart.chart_file.url)
            return obj.chart.chart_file.url
        return None


class PeerReviewSerializer(serializers.ModelSerializer):
    """互评记录序列化器（包含评分内容）"""
    
    class Meta:
        model = PeerReview
        fields = ('id', 'score', 'comment', 'created_at')
        read_only_fields = ('id', 'created_at')


class PeerReviewSubmitSerializer(serializers.ModelSerializer):
    """互评提交序列化器"""
    
    class Meta:
        model = PeerReview
        fields = ('score', 'comment')
        extra_kwargs = {
            'score': {'required': True},
            'comment': {'required': False},
        }
    
    def validate_score(self, value):
        """验证评分范围"""
        from .models import PEER_REVIEW_MAX_SCORE
        if value < 0 or value > PEER_REVIEW_MAX_SCORE:
            raise serializers.ValidationError(
                f'评分必须在0-{PEER_REVIEW_MAX_SCORE}之间'
            )
        return value


class ChartDetailSerializer(serializers.ModelSerializer):
    """谱面详情序列化器（包含评分统计）"""
    song = SongListSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    chart_file_url = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Chart
        fields = (
            'id', 'username', 'song', 'status', 'status_display', 'designer',
            'audio_file', 'audio_url', 'cover_image', 'cover_url', 'chart_file', 'chart_file_url',
            'review_count', 'total_score', 'average_score',
            'reviews', 'created_at', 'submitted_at', 'review_completed_at'
        )
        read_only_fields = fields

    def _build_url(self, request, field):
        if field:
            return request.build_absolute_uri(field.url) if request else field.url
        return None

    def get_chart_file_url(self, obj):
        """获取谱面文件的完整URL"""
        request = self.context.get('request') if hasattr(self, 'context') else None
        return self._build_url(request, obj.chart_file)

    def get_audio_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        return self._build_url(request, obj.audio_file)

    def get_cover_url(self, obj):
        request = self.context.get('request') if hasattr(self, 'context') else None
        return self._build_url(request, obj.cover_image)
    
    def get_reviews(self, obj):
        """获取该谱面的所有评分（匿名）"""
        reviews = PeerReview.objects.filter(
            chart=obj
        ).values('score', 'comment', 'created_at').order_by('-created_at')
        return PeerReviewSerializer(reviews, many=True).data


# ==================== 第二轮竞标相关序列化器（已废弃） ====================
# 注意：以下代码已被注释，现在使用统一的Bid/BidResult序列化器来处理歌曲和谱面竞标

# from .models import SecondBiddingRound, SecondBid, SecondBidResult


# class SecondBiddingRoundSerializer(serializers.ModelSerializer):
#     """第二轮竞标轮次序列化器"""
#     status_display = serializers.CharField(source='get_status_display', read_only=True)
#     bidding_round_name = serializers.CharField(source='first_bidding_round.name', read_only=True)
#     
#     class Meta:
#         model = SecondBiddingRound
#         fields = (
#             'id', 'first_bidding_round', 'bidding_round_name', 'status', 'status_display',
#             'created_at', 'started_at', 'completed_at'
#         )
#         read_only_fields = ('id', 'created_at')


# class AvailableChartSerializer(serializers.ModelSerializer):
#     """可竞标的一半谱面序列化器"""
#     song = SongListSerializer(read_only=True)
#     creator_username = serializers.CharField(source='user.username', read_only=True)
#     part_one_chart_url = serializers.CharField(source='part_one_chart.chart_url', read_only=True, required=False)
#     part_one_chart_id_external = serializers.CharField(
#         source='part_one_chart.chart_id_external', read_only=True, required=False
#     )
#     
#     class Meta:
#         model = Chart
#         fields = (
#             'id', 'song', 'creator_username', 'part_one_chart_url', 'part_one_chart_id_external',
#             'average_score', 'created_at'
#         )
#         read_only_fields = fields


# class SecondBidSerializer(serializers.ModelSerializer):
#     """第二轮竞标序列化器"""
#     song_title = serializers.CharField(source='target_chart_part_one.song.title', read_only=True)
#     creator_username = serializers.CharField(source='target_chart_part_one.user.username', read_only=True)
#     bidder_username = serializers.CharField(source='bidder.username', read_only=True)
#     
#     class Meta:
#         model = SecondBid
#         fields = (
#             'id', 'target_chart_part_one', 'song_title', 'creator_username',
#             'bidder_username', 'amount', 'is_dropped', 'created_at'
#         )
#         read_only_fields = ('id', 'bidder_username', 'is_dropped', 'created_at')
#     
#     def validate_amount(self, value):
#         """验证竞标金额"""
#         if value <= 0:
#             raise serializers.ValidationError('竞标金额必须大于0')
#         if value > 999:
#             raise serializers.ValidationError('竞标金额不能超过999')
#         return value
#     
#     def validate(self, data):
#         """验证不能对自己的谱面进行竞标"""
#         user = self.context['request'].user
#         target_chart = data.get('target_chart_part_one')
#         
#         if target_chart and target_chart.user == user:
#             raise serializers.ValidationError('不能对自己的谱面进行竞标')
#         
#         return data


# class SecondBidResultSerializer(serializers.ModelSerializer):
#     """第二轮竞标结果序列化器"""
#     song_title = serializers.CharField(source='part_one_chart.song.title', read_only=True)
#     part_one_creator_username = serializers.CharField(
#         source='part_one_chart.user.username', read_only=True
#     )
#     winner_username = serializers.CharField(source='winner.username', read_only=True)
#     allocation_type_display = serializers.CharField(source='get_allocation_type_display', read_only=True)
#     completed_chart_id = serializers.IntegerField(source='completed_chart.id', read_only=True, required=False)
#     
#     class Meta:
#         model = SecondBidResult
#         fields = (
#             'id', 'song_title', 'part_one_creator_username', 'winner_username',
#             'allocation_type', 'allocation_type_display', 'completed_chart_id', 'allocated_at'
#         )
#         read_only_fields = fields


class BannerSerializer(serializers.ModelSerializer):
    """Banner 序列化器 - 自动处理nginx反向代理下的图片URL"""
    
    def to_representation(self, instance):
        """自定义序列化输出，处理图片URL"""
        data = super().to_representation(instance)
        
        # 处理image_url以适配nginx反向代理
        if data.get('image_url'):
            image_url = data['image_url']
            
            # 如果是完整的localhost开发地址，转换为相对路径
            if 'localhost:8000' in image_url:
                # 提取路径部分（/media/... 或 /static/...）
                import re
                path_match = re.search(r'/(media|static)/.*$', image_url)
                if path_match:
                    data['image_url'] = path_match.group(0)
            
            # 确保相对路径以 / 开头
            elif image_url and not image_url.startswith(('http://', 'https://', '/')):
                data['image_url'] = f'/{image_url}'
        
        return data
    
    class Meta:
        model = Banner
        fields = ('id', 'title', 'content', 'image_url', 'link', 'button_text', 'color', 'priority')


class AnnouncementSerializer(serializers.ModelSerializer):
    """公告序列化器"""
    class Meta:
        model = Announcement
        fields = ('id', 'title', 'content', 'category', 'is_pinned', 'created_at', 'updated_at')


class CompetitionPhaseSerializer(serializers.ModelSerializer):
    """比赛阶段序列化器"""
    status = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    
    class Meta:
        model = CompetitionPhase
        fields = (
            'id',
            'name',
            'phase_key',
            'description',
            'start_time',
            'end_time',
            'order',
            'status',
            'time_remaining',
            'progress_percent',
            'page_access',
            'is_active',
        )
        read_only_fields = ('status', 'time_remaining', 'progress_percent')
    
    def get_status(self, obj):
        """获取阶段状态"""
        return obj.status
    
    def get_time_remaining(self, obj):
        """获取剩余时间"""
        return obj.get_time_remaining()
    
    def get_progress_percent(self, obj):
        """获取进度百分比"""
        return obj.get_progress_percent()
