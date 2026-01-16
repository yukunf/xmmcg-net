import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# ==================== 可调整的常量 ====================
# 每个用户可上传的歌曲数量限制
MAX_SONGS_PER_USER = 2

# 每个用户可以竞标的歌曲数量限制
MAX_BIDS_PER_USER = 5


def get_audio_filename(instance, filename):
    """
    生成音频文件名
    格式: audio_user{user_id}_song{song_id}.{ext}
    例: audio_user1_song5.mp3
    """
    ext = filename.split('.')[-1].lower()
    return f'songs/audio_user{instance.user.id}_song{instance.id}.{ext}'


def get_cover_filename(instance, filename):
    """
    生成封面文件名
    格式: cover_user{user_id}_song{song_id}.{ext}
    例: cover_user1_song5.jpg
    """
    ext = filename.split('.')[-1].lower()
    return f'songs/cover_user{instance.user.id}_song{instance.id}.{ext}'


class Song(models.Model):
    """用户上传的歌曲模型"""
    
    # 主键
    id = models.AutoField(primary_key=True)
    
    # 唯一标识（内部使用，用于去重识别）
    unique_key = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    # 用户关系（ForeignKey 允许多首歌）
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='songs'
    )
    
    # 歌曲信息
    title = models.CharField(
        max_length=100,
        help_text='歌曲标题'
    )
    audio_file = models.FileField(
        upload_to=get_audio_filename,
        help_text='音频文件'
    )
    cover_image = models.ImageField(
        upload_to=get_cover_filename,
        null=True,
        blank=True,
        help_text='封面图片（可选）'
    )
    netease_url = models.URLField(
        null=True,
        blank=True,
        help_text='网易云音乐链接（可选）'
    )
    
    # 文件标识和大小
    audio_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text='音频文件 SHA256 hash，用于识别重复'
    )
    file_size = models.IntegerField(
        help_text='音频文件大小（字节）'
    )
    
    # 时间戳
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='最后更新时间'
    )
    
    class Meta:
        ordering = ['-id']  # 最新的歌曲在前
        verbose_name = '歌曲'
        verbose_name_plural = '歌曲'
    
    def __str__(self):
        return f"#{self.id} - {self.title} (by {self.user.username})"
    
    def delete(self, *args, **kwargs):
        """删除歌曲时同时删除关联文件"""
        if self.audio_file:
            self.audio_file.delete(save=False)
        if self.cover_image:
            self.cover_image.delete(save=False)
        super().delete(*args, **kwargs)


class BiddingRound(models.Model):
    """竞标轮次"""
    
    STATUS_CHOICES = [
        ('pending', '待开始'),
        ('active', '进行中'),
        ('completed', '已完成'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text='竞标轮次名称'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='竞标状态'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='创建时间'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='开始时间'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='完成时间'
    )
    
    class Meta:
        verbose_name = '竞标轮次'
        verbose_name_plural = '竞标轮次'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Bid(models.Model):
    """用户竞标（用户对歌曲的出价）"""
    
    bidding_round = models.ForeignKey(
        BiddingRound,
        on_delete=models.CASCADE,
        related_name='bids',
        help_text='所属竞标轮次'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bids',
        help_text='竞标用户'
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='bids',
        help_text='目标歌曲'
    )
    amount = models.IntegerField(
        help_text='竞标金额（代币）'
    )
    is_dropped = models.BooleanField(
        default=False,
        help_text='是否已被drop（歌曲被更高出价者获得）'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='竞标时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='最后更新时间'
    )
    
    class Meta:
        # 一个用户在同一轮竞标中，对同一歌曲只能出价一次
        unique_together = ('bidding_round', 'user', 'song')
        verbose_name = '竞标'
        verbose_name_plural = '竞标'
        ordering = ['-amount', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} 竞标 {self.song.title} - {self.amount}代币"
    
    def clean(self):
        """验证竞标"""
        # 验证用户在该轮次中的竞标数量不超过限制
        bid_count = Bid.objects.filter(
            bidding_round=self.bidding_round,
            user=self.user,
            is_dropped=False
        ).exclude(song=self.song).count()
        
        if bid_count >= MAX_BIDS_PER_USER:
            raise ValidationError(
                f'超过每轮最多竞标 {MAX_BIDS_PER_USER} 个歌曲的限制'
            )
        
        # 验证竞标金额
        if self.amount <= 0:
            raise ValidationError('竞标金额必须大于0')


class BidResult(models.Model):
    """竞标结果（分配结果）"""
    
    ALLOCATION_TYPE_CHOICES = [
        ('win', '中标'),
        ('random', '随机分配'),
    ]
    
    bidding_round = models.ForeignKey(
        BiddingRound,
        on_delete=models.CASCADE,
        related_name='results',
        help_text='所属竞标轮次'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bid_results',
        help_text='获得歌曲的用户'
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='bid_results',
        help_text='分配的歌曲'
    )
    bid_amount = models.IntegerField(
        help_text='最终成交的竞标金额'
    )
    allocation_type = models.CharField(
        max_length=20,
        choices=ALLOCATION_TYPE_CHOICES,
        default='win',
        help_text='分配类型（中标或随机分配）'
    )
    allocated_at = models.DateTimeField(
        auto_now_add=True,
        help_text='分配时间'
    )
    
    class Meta:
        # 一个用户在同一轮竞标中，对同一歌曲只能有一个分配结果
        unique_together = ('bidding_round', 'user', 'song')
        verbose_name = '竞标结果'
        verbose_name_plural = '竞标结果'
        ordering = ['-allocated_at']
    
    def __str__(self):
        allocation_type_display = dict(self.ALLOCATION_TYPE_CHOICES)[self.allocation_type]
        return f"{self.user.username} {allocation_type_display} {self.song.title} - {self.bid_amount}代币"
