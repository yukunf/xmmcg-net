import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# ==================== 可调整的常量 ====================
# 每个用户可上传的歌曲数量限制
MAX_SONGS_PER_USER = 3

# 每个用户可以竞标的歌曲数量限制
MAX_BIDS_PER_USER = 5

# 保底分配需要扣除的代币数量
RANDOM_ALLOCATION_COST = 200

# 互评系统常量（已迁移到settings.py，此处保留用于向后兼容）
# 推荐：在settings.py中设置 PEER_REVIEW_TASKS_PER_USER 和 PEER_REVIEW_MAX_SCORE
PEER_REVIEW_TASKS_PER_USER = 8  # 每个用户需要完成的评分任务数（可在settings.py覆盖）
PEER_REVIEW_MAX_SCORE = 50      # 互评满分（可在settings.py覆盖）

# 背景视频常量
MAX_VIDEO_SIZE_MB = 20          # 背景视频最大文件大小（MB）


# ==================== Banner 与公告 ====================

class Banner(models.Model):
    """首页轮换 Banner"""
    title = models.CharField(max_length=100, help_text='Banner 标题')
    content = models.TextField(help_text='Banner 描述内容')
    image_url = models.CharField(null=True, blank=True, help_text='背景图片 URL（可选）')
    link = models.URLField(null=True, blank=True, help_text='点击跳转链接（可选）')
    button_text = models.CharField(max_length=50, default='了解更多', help_text='按钮文本')
    color = models.CharField(max_length=20, default='#409EFF', help_text='背景色')
    priority = models.IntegerField(default=0, help_text='优先级，越大越靠前')
    is_active = models.BooleanField(default=True, help_text='是否启用')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Banner'
        verbose_name_plural = 'Banner'
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"{self.title} ({'启用' if self.is_active else '禁用'})"


class Announcement(models.Model):
    """首页公告"""
    CATEGORY_CHOICES = [
        ('news', '新闻'),
        ('event', '活动'),
        ('notice', '通知'),
    ]

    title = models.CharField(max_length=200, help_text='公告标题')
    content = models.TextField(help_text='公告内容（支持 Markdown）')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='news', help_text='公告分类')
    priority = models.IntegerField(default=0, help_text='优先级，越大越靠前')
    is_pinned = models.BooleanField(default=False, help_text='是否置顶')
    is_active = models.BooleanField(default=True, help_text='是否启用')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '公告'
        verbose_name_plural = '公告'
        ordering = ['-is_pinned', '-priority', '-created_at']

    def __str__(self):
        return f"{self.title} ({'启用' if self.is_active else '禁用'})"


# ==================== 比赛阶段管理 ====================

def get_default_page_access():
    """默认页面访问权限配置"""
    return {
        "songs": True,
        "charts": True,
        "profile": True,
        "eval": True,
    }


class CompetitionPhase(models.Model):
    """比赛阶段管理模型（用于时间控制和权限管理）"""
    
    # 统计类型选择
    SUBMISSIONS_TYPE_CHOICES = [
        ('songs', '歌曲数'),
        ('charts', '谱面数'),
    ]
    
    # 阶段信息
    name = models.CharField(max_length=100, help_text='阶段名称，如"竞标期"、"制谱期"')
    phase_key = models.CharField(
        max_length=50, 
        unique=True, 
        help_text='唯一标识符，用于权限绑定。如 bidding、mapping、peer_review'
    )
    description = models.TextField(help_text='阶段描述，显示在主页时间轴')
    
    # 统计类型配置
    submissions_type = models.CharField(
        max_length=20,
        choices=SUBMISSIONS_TYPE_CHOICES,
        default='songs',
        help_text='该阶段统计的作品类型（显示在首页）'
    )
    
    # 时间设置
    start_time = models.DateTimeField(help_text='阶段开始时间')
    end_time = models.DateTimeField(help_text='阶段结束时间')
    
    # 显示和权限
    order = models.PositiveIntegerField(default=0, help_text='显示顺序（从小到大）')
    is_active = models.BooleanField(default=True, help_text='是否启用此阶段')
    
    # 页面访问权限配置（JSON 格式）
    page_access = models.JSONField(
        default=get_default_page_access,
        help_text='页面访问权限配置，如 {"songs": true, "charts": false, "profile": true, "eval": true}（注：首页、登录、注册页总是可访问）'
    )
    
    # 系统字段
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '比赛阶段'
        verbose_name_plural = '比赛阶段'
        ordering = ['order', 'start_time']
    
    def __str__(self):
        return f"{self.name} ({self.phase_key}) - {self.status}"
    
    @property
    def status(self):
        """
        实时计算阶段状态
        - upcoming: 即将开始（当前时间 < 开始时间）
        - active: 进行中（开始时间 ≤ 当前时间 ≤ 结束时间）
        - ended: 已结束（当前时间 > 结束时间）
        """
        from django.utils import timezone
        now = timezone.now()
        if now < self.start_time:
            return 'upcoming'
        elif now <= self.end_time:
            return 'active'
        else:
            return 'ended'
    
    def get_time_remaining(self):
        """获取剩余时间字符串"""
        from django.utils import timezone
        now = timezone.now()
        
        if self.status == 'upcoming':
            delta = self.start_time - now
        elif self.status == 'active':
            delta = self.end_time - now
        else:
            return '已结束'
        
        days = delta.days
        hours = delta.seconds // 3600
        
        if days > 0:
            return f'{days} 天 {hours} 小时'
        else:
            return f'{hours} 小时'
    
    def get_progress_percent(self):
        """获取阶段进度百分比（进行中返回进度，其他返回 0 或 100）"""
        from django.utils import timezone
        now = timezone.now()
        
        if self.status == 'upcoming':
            return 0
        elif self.status == 'ended':
            return 100
        else:
            # 进行中：计算百分比
            total_duration = (self.end_time - self.start_time).total_seconds()
            elapsed = (now - self.start_time).total_seconds()
            return max(0, min(100, int((elapsed / total_duration) * 100)))


def get_audio_filename(instance, filename):
    """
    生成音频文件名
    格式: audio_user{user_id}_{uuid}.{ext}
    例: audio_user1_a1b2c3d4.mp3
    """
    import uuid as uuid_lib
    ext = filename.split('.')[-1].lower()
    unique_id = uuid_lib.uuid4().hex[:8]
    return f'songs/audio_user{instance.user.id}_{unique_id}.{ext}'


def get_cover_filename(instance, filename):
    """
    生成封面文件名
    格式: cover_user{user_id}_{uuid}.{ext}
    例: cover_user1_a1b2c3d4.jpg
    """
    import uuid as uuid_lib
    ext = filename.split('.')[-1].lower()
    unique_id = uuid_lib.uuid4().hex[:8]
    return f'songs/cover_user{instance.user.id}_{unique_id}.{ext}'


def get_video_filename(instance, filename):
    """
    生成背景视频文件名
    格式: video_user{user_id}_{uuid}.{ext}
    例: video_user1_a1b2c3d4.mp4
    """
    import uuid as uuid_lib
    ext = filename.split('.')[-1].lower()
    unique_id = uuid_lib.uuid4().hex[:8]
    return f'songs/video_user{instance.user.id}_{unique_id}.{ext}'


def get_chart_filename(instance, filename):
    """
    生成谱面文件名（固定为maidata.txt）
    格式: charts/user{user_id}_song{song_id}_{uuid}/maidata.txt
    例: charts/user1_song5_a1b2c3d4/maidata.txt
    """
    import uuid as uuid_lib
    unique_id = uuid_lib.uuid4().hex[:8]
    return f'charts/user{instance.user.id}_song{instance.song.id}_{unique_id}/maidata.txt'


def get_chart_audio_filename(instance, filename):
    """生成谱面音频文件名"""
    import uuid as uuid_lib
    ext = filename.split('.')[-1].lower()
    unique_id = uuid_lib.uuid4().hex[:8]
    return f'charts/audio_user{instance.user.id}_song{instance.song.id}_{unique_id}.{ext}'


def get_chart_cover_filename(instance, filename):
    """生成谱面封面文件名"""
    import uuid as uuid_lib
    ext = filename.split('.')[-1].lower()
    unique_id = uuid_lib.uuid4().hex[:8]
    return f'charts/cover_user{instance.user.id}_song{instance.song.id}_{unique_id}.{ext}'


def get_chart_video_filename(instance, filename):
    """生成谱面背景视频文件名"""
    import uuid as uuid_lib
    ext = filename.split('.')[-1].lower()
    unique_id = uuid_lib.uuid4().hex[:8]
    return f'charts/video_user{instance.user.id}_song{instance.song.id}_{unique_id}.{ext}'


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
    background_video = models.FileField(
        upload_to=get_video_filename,
        null=True,
        blank=True,
        help_text='背景视频（bg.mp4或pv.mp4，最大20MB，可选）'
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
        if self.background_video:
            self.background_video.delete(save=False)
        super().delete(*args, **kwargs)


class BiddingRound(models.Model):
    """竞标轮次（统一支持歌曲和谱面竞标）"""
    
    STATUS_CHOICES = [
        ('pending', '待开始'),
        ('active', '进行中'),
        ('completed', '已完成'),
    ]
    
    BIDDING_TYPE_CHOICES = [
        ('song', '歌曲竞标'),
        ('chart', '谱面竞标'),
    ]
    
    # 关联比赛阶段
    competition_phase = models.ForeignKey(
        CompetitionPhase,
        on_delete=models.CASCADE,
        related_name='bidding_rounds',
        null=True,
        blank=True,
        help_text='所属比赛阶段（可选，用于与比赛流程关联）'
    )
    
    # 竞标类型
    bidding_type = models.CharField(
        max_length=20,
        choices=BIDDING_TYPE_CHOICES,
        default='song',
        help_text='竞标类型：歌曲竞标或谱面竞标'
    )
    
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
    
    
    # 新增加的控制访问字段
    allow_public_view = models.BooleanField(
        default=True, 
        verbose_name="允许公开查看竞标",
        help_text="如果关闭，只有管理员能看到竞标列表，普通用户（包括竞标者）无法查看。"
    )
    class Meta:
        verbose_name = '竞标轮次'
        verbose_name_plural = '竞标轮次'
        ordering = ['-created_at']
    
    def __str__(self):
        type_display = self.get_bidding_type_display()
        return f"{self.name} ({type_display} - {self.get_status_display()})"


class Bid(models.Model):
    """用户竞标（用户对歌曲或谱面的出价）"""
    
    BID_TYPE_CHOICES = [
        ('song', '歌曲竞标'),
        ('chart', '谱面竞标'),
    ]
    
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
    
    # 竞标类型（与BiddingRound.bidding_type对应）
    bid_type = models.CharField(
        max_length=20,
        choices=BID_TYPE_CHOICES,
        default='song',
        help_text='竞标类型：歌曲或谱面'
    )
    
    # 竞标目标（二选一）
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='bids',
        null=True,
        blank=True,
        help_text='目标歌曲（仅当bid_type=song时使用）'
    )
    chart = models.ForeignKey(
        'Chart',
        on_delete=models.CASCADE,
        related_name='bids',
        null=True,
        blank=True,
        help_text='目标谱面（仅当bid_type=chart时使用）'
    )
    
    amount = models.IntegerField(
        help_text='竞标金额（代币）'
    )
    is_dropped = models.BooleanField(
        default=False,
        help_text='是否已被drop（被更高出价者获得）'
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
        verbose_name = '竞标'
        verbose_name_plural = '竞标'
        ordering = ['-amount', '-created_at']
    
    def __str__(self):
        target = self.song.title if self.song else (f"{self.chart.user.username}的谱面" if self.chart else "未知")
        return f"{self.user.username} 竞标 {target} - {self.amount}代币"
    
    def clean(self):
        """验证竞标"""
        # 验证bid_type与song/chart的一致性
        if self.bid_type == 'song' and not self.song:
            raise ValidationError('歌曲竞标必须指定目标歌曲')
        if self.bid_type == 'chart' and not self.chart:
            raise ValidationError('谱面竞标必须指定目标谱面')
        if self.song and self.chart:
            raise ValidationError('不能同时竞标歌曲和谱面')
        if not self.song and not self.chart:
            raise ValidationError('必须指定竞标目标（歌曲或谱面）')
        
        # 对于谱面竞标，已改为可以竞标自己的谱面
        # if self.bid_type == 'chart' and self.chart and self.chart.user == self.user:
        #     raise ValidationError('不能竞标自己的谱面')
        
        # 验证用户在该轮次中的竞标数量不超过限制
        bid_count = Bid.objects.filter(
            bidding_round=self.bidding_round,
            user=self.user,
            is_dropped=False
        ).exclude(id=self.id).count()
        
        if bid_count >= MAX_BIDS_PER_USER:
            raise ValidationError(
                f'超过每轮最多竞标 {MAX_BIDS_PER_USER} 个的限制'
            )
        
        # 验证竞标金额
        if self.amount <= 0:
            raise ValidationError('竞标金额必须大于0')
    
    @property
    def target(self):
        """获取竞标目标对象（song或chart）"""
        return self.song if self.bid_type == 'song' else self.chart



class BidResult(models.Model):
    """竞标结果（分配结果）"""
    
    ALLOCATION_TYPE_CHOICES = [
        ('win', '中标'),
        ('random', '随机分配'),
    ]
    
    BID_TYPE_CHOICES = [
        ('song', '歌曲竞标'),
        ('chart', '谱面竞标'),
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
        help_text='获得歌曲或谱面的用户'
    )
    
    # 分配类型
    bid_type = models.CharField(
        max_length=20,
        choices=BID_TYPE_CHOICES,
        default='song',
        help_text='分配类型：歌曲或谱面'
    )
    
    # 分配的目标（二选一）
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='bid_results',
        null=True,
        blank=True,
        help_text='分配的歌曲（仅当bid_type=song时使用）'
    )
    chart = models.ForeignKey(
        'Chart',
        on_delete=models.CASCADE,
        related_name='bid_results',
        null=True,
        blank=True,
        help_text='分配的谱面（仅当bid_type=chart时使用）'
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
        verbose_name = '竞标结果'
        verbose_name_plural = '竞标结果'
        ordering = ['-allocated_at']
    
    def __str__(self):
        allocation_type_display = self.get_allocation_type_display()
        target = self.song.title if self.song else (f"{self.chart.user.username}的谱面" if self.chart else "未知")
        return f"{self.user.username} {allocation_type_display} {target} - {self.bid_amount}代币"
    
    def clean(self):
        """验证分配结果"""
        if self.bid_type == 'song' and not self.song:
            raise ValidationError('歌曲分配必须指定目标歌曲')
        if self.bid_type == 'chart' and not self.chart:
            raise ValidationError('谱面分配必须指定目标谱面')
        if self.song and self.chart:
            raise ValidationError('不能同时分配歌曲和谱面')
        if not self.song and not self.chart:
            raise ValidationError('必须指定分配目标（歌曲或谱面）')
    
    @property
    def target(self):
        """获取分配目标对象（song或chart）"""
        return self.song if self.bid_type == 'song' else self.chart


class Chart(models.Model):
    """用户提交的谱面（beatmap）"""
    
    STATUS_CHOICES = [
        ('part_submitted', '半成品'),
        ('final_submitted', '完稿'),
        ('under_review', '评分中'),
        ('reviewed', '已评分'),
    ]
    
    # 关系
    bidding_round = models.ForeignKey(
        BiddingRound,
        on_delete=models.CASCADE,
        related_name='charts',
        help_text='所属竞标轮次'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='charts',
        help_text='谱面创建者'
    )
    song = models.ForeignKey(
        Song,
        on_delete=models.CASCADE,
        related_name='charts',
        help_text='谱面对应的歌曲'
    )
    bid_result = models.ForeignKey(
        BidResult,
        on_delete=models.CASCADE,
        related_name='charts',
        null=True,
        blank=True,
        help_text='对应的竞标结果（第一部分必需，第二部分可选）'
    )
    
    # 谱面信息
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='part_submitted',
        help_text='谱面状态'
    )
    designer = models.CharField(
        max_length=100,
        default='未填写',
        help_text='谱师名义'
    )

    # 上传资源（第一阶段半成品需要打包文件）
    audio_file = models.FileField(
        upload_to=get_chart_audio_filename,
        null=True,
        blank=True,
        help_text='谱面对应音频文件'
    )
    cover_image = models.ImageField(
        upload_to=get_chart_cover_filename,
        null=True,
        blank=True,
        help_text='谱面封面图片'
    )
    background_video = models.FileField(
        upload_to=get_chart_video_filename,
        null=True,
        blank=True,
        help_text='谱面背景视频（可选）'
    )
    
    # 谱面文件（本地托管，文件名固定为maidata.txt）
    chart_file = models.FileField(
        upload_to=get_chart_filename,
        null=True,
        blank=True,
        help_text='谱面文件（maidata.txt）'
    )
    
    # 时间戳
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='创建时间'
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='提交时间'
    )
    review_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='评分完成时间'
    )
    
    # 评分统计（冗余字段，便于查询）
    review_count = models.IntegerField(
        default=0,
        help_text='收到的评分数'
    )
    total_score = models.IntegerField(
        default=0,
        help_text='总评分（用于快速计算平均分）'
    )
    average_score = models.FloatField(
        default=0.0,
        help_text='平均分（0-50）'
    )
    
    # 二部分谱面支持（第二轮竞标续写）
    is_part_one = models.BooleanField(
        default=True,
        help_text='是否是第一部分谱面（True=第一部分，False=第二部分）'
    )
    part_one_chart = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='part_two_chart',
        help_text='如果是第二部分，指向对应的第一部分谱面'
    )
    completion_bid_result = models.ForeignKey(
        BidResult,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completion_charts',
        help_text='第二轮竞标获得的一部分，用于续写'
    )
    
    class Meta:
        verbose_name = '谱面'
        verbose_name_plural = '谱面'
        ordering = ['-created_at']
        # 一个用户对同一歌曲在同一轮中只能提交一个谱面
        unique_together = ('bidding_round', 'user', 'song')
    
    def __str__(self):
        part_info = '（二部分）' if not self.is_part_one else ''
        return f"{self.user.username} - {self.song.title} {part_info}({self.get_status_display()})"
    
    def delete(self, *args, **kwargs):
        """删除谱面时同时删除关联的谱面文件"""
        if self.chart_file:
            self.chart_file.delete(save=False)
        if self.audio_file:
            self.audio_file.delete(save=False)
        if self.cover_image:
            self.cover_image.delete(save=False)
        if self.background_video:
            self.background_video.delete(save=False)
        super().delete(*args, **kwargs)


class PeerReviewAllocation(models.Model):
    """互评任务分配（保证每个选手收到8个评分，每个评分者评分8个选手）"""
    
    bidding_round = models.ForeignKey(
        BiddingRound,
        on_delete=models.CASCADE,
        related_name='peer_review_allocations',
        help_text='所属竞标轮次'
    )
    
    # 分配信息
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assigned_peer_reviews',
        help_text='评分者'
    )
    
    chart = models.ForeignKey(
        Chart,
        on_delete=models.CASCADE,
        related_name='review_allocations',
        help_text='被评分的谱面'
    )
    
    # 状态
    STATUS_CHOICES = [
        ('pending', '待评分'),
        ('completed', '已完成'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='任务状态'
    )
    
    # 时间戳
    allocated_at = models.DateTimeField(
        auto_now_add=True,
        help_text='分配时间'
    )
    
    class Meta:
        verbose_name = '互评分配'
        verbose_name_plural = '互评分配'
        ordering = ['allocated_at']
        # 同一个评分者不能多次评同一个谱面
        unique_together = ('reviewer', 'chart')
    
    def __str__(self):
        return f"{self.reviewer.username} -> {self.chart.user.username}的{self.chart.song.title}"


class PeerReview(models.Model):
    """互评打分记录"""
    
    # 关系
    allocation = models.OneToOneField(
        PeerReviewAllocation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='review',
        help_text='对应的分配任务（系统分配的任务有allocation，额外评分没有）'
    )
    
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_peer_reviews',
        help_text='评分者'
    )
    
    chart = models.ForeignKey(
        Chart,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text='被评分的谱面'
    )
    
    # 评分内容
    score = models.IntegerField(
        help_text='评分'
    )
    
    comment = models.TextField(
        blank=True,
        null=True,
        help_text='评论（可选）'
    )
    
    favorite = models.BooleanField(
        default=False,
        help_text='是否标记为喜欢',
        null=False,
        blank=False
    )
    # 时间戳
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='评分时间'
    )
    
    class Meta:
        verbose_name = '互评记录'
        verbose_name_plural = '互评记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.reviewer.username} 给 {self.chart.user.username} 打分 {self.score}"
    
    def clean(self):
        """验证评分"""
        if self.score < 0 or self.score > PEER_REVIEW_MAX_SCORE:
            raise ValidationError(
                f'评分必须在0-{PEER_REVIEW_MAX_SCORE}之间'
            )


# ==================== 第二轮竞标系统（已废弃，使用统一的Bid系统） ====================
# 注意：以下代码已被注释，现在使用统一的Bid/BidResult系统来处理歌曲和谱面竞标
# 请使用 BiddingRound.bidding_type='chart' 来进行谱面竞标

# class SecondBiddingRound(models.Model):
#     """第二轮竞标轮次（竞标其他选手已提交的一半谱面来续写）"""
#     
#     STATUS_CHOICES = [
#         ('pending', '待开始'),
#         ('active', '进行中'),
#         ('completed', '已完成'),
#     ]
#     
#     # 关联的第一轮竞标
#     first_bidding_round = models.OneToOneField(
#         BiddingRound,
#         on_delete=models.CASCADE,
#         related_name='second_bidding_round',
#         help_text='对应的第一轮竞标轮次'
#     )
#     
#     # 状态
#     status = models.CharField(
#         max_length=20,
#         choices=STATUS_CHOICES,
#         default='pending',
#         help_text='第二轮竞标状态'
#     )
#     
#     # 说明：参与者为第一轮的所有竞标者，可竞标标的为其他人已提交的一半谱面
#     name = models.CharField(
#         max_length=100,
#         help_text='第二轮名称'
#     )
#     
#     # 时间戳
#     created_at = models.DateTimeField(
#         auto_now_add=True,
#         help_text='创建时间'
#     )
#     started_at = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text='开始时间'
#     )
#     completed_at = models.DateTimeField(
#         null=True,
#         blank=True,
#         help_text='完成时间'
#     )
#     
#     class Meta:
#         verbose_name = '第二轮竞标轮次'
#         verbose_name_plural = '第二轮竞标轮次'
#         ordering = ['-created_at']
#     
#     def __str__(self):
#         return f"{self.name} ({self.get_status_display()})"


# class SecondBid(models.Model):
#     """第二轮竞标（用户竞标其他人的一半谱面）"""
#     
#     second_bidding_round = models.ForeignKey(
#         SecondBiddingRound,
#         on_delete=models.CASCADE,
#         related_name='second_bids',
#         help_text='所属第二轮竞标轮次'
#     )
#     
#     bidder = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         related_name='second_bids',
#         help_text='竞标者（需要续写的选手）'
#     )
#     
#     # 标的物：第一轮已提交的一半谱面
#     target_chart_part_one = models.ForeignKey(
#         Chart,
#         on_delete=models.CASCADE,
#         related_name='second_bids',
#         help_text='竞标的目标：其他选手的一半谱面'
#     )
#     
#     # 竞标金额（从剩余token中消耗）
#     amount = models.IntegerField(
#         help_text='竞标金额（代币）'
#     )
#     
#     # 状态
#     is_dropped = models.BooleanField(
#         default=False,
#         help_text='是否已被drop（被更高出价者竞走）'
#     )
#     
#     # 时间戳
#     created_at = models.DateTimeField(
#         auto_now_add=True,
#         help_text='竞标时间'
#     )
#     updated_at = models.DateTimeField(
#         auto_now=True,
#         help_text='最后更新时间'
#     )
#     
#     class Meta:
#         verbose_name = '第二轮竞标'
#         verbose_name_plural = '第二轮竞标'
#         ordering = ['-amount', '-created_at']
#         # 同一选手在同一轮次中，对同一个一半谱面只能出价一次
#         unique_together = ('second_bidding_round', 'bidder', 'target_chart_part_one')
#     
#     def __str__(self):
#         return f"{self.bidder.username} 竞标 {self.target_chart_part_one.user.username}的一半谱面 - {self.amount}代币"
#     
#     def clean(self):
#         """验证第二轮竞标"""
#         # 不能竞标自己的谱面
#         if self.bidder == self.target_chart_part_one.user:
#             raise ValidationError('不能竞标自己的谱面')
#         
#         # 验证竞标金额
#         if self.amount <= 0:
#             raise ValidationError('竞标金额必须大于0')


# class SecondBidResult(models.Model):
#     """第二轮竞标结果（分配结果）"""
#     
#     ALLOCATION_TYPE_CHOICES = [
#         ('win', '中标'),
#         ('random', '随机分配'),
#     ]
#     
#     second_bidding_round = models.ForeignKey(
#         SecondBiddingRound,
#         on_delete=models.CASCADE,
#         related_name='second_results',
#         help_text='所属第二轮竞标轮次'
#     )
#     
#     winner = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         related_name='second_bid_results',
#         help_text='获得一半谱面的选手（续写者）'
#     )
#     
#     # 获得的一半谱面
#     part_one_chart = models.ForeignKey(
#         Chart,
#         on_delete=models.CASCADE,
#         related_name='second_bid_results',
#         help_text='获得的第一部分谱面'
#     )
#     
#     # 最终成交价格
#     bid_amount = models.IntegerField(
#         help_text='最终成交的竞标金额'
#     )
#     
#     # 分配类型
#     allocation_type = models.CharField(
#         max_length=20,
#         choices=ALLOCATION_TYPE_CHOICES,
#         default='win',
#         help_text='分配类型（中标或随机分配）'
#     )
#     
#     # 时间戳
#     allocated_at = models.DateTimeField(
#         auto_now_add=True,
#         help_text='分配时间'
#     )
#     
#     # 关联的完成谱面（二部分）
#     completed_chart = models.OneToOneField(
#         Chart,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='second_bid_result_completion',
#         help_text='基于此分配创建的完成谱面'
#     )
#     
#     class Meta:
#         verbose_name = '第二轮竞标结果'
#         verbose_name_plural = '第二轮竞标结果'
#         ordering = ['-allocated_at']
#         # 同一选手对同一个一半谱面只能有一个分配结果
#         unique_together = ('second_bidding_round', 'winner', 'part_one_chart')
#     
#     def __str__(self):
#         allocation_type_display = dict(self.ALLOCATION_TYPE_CHOICES)[self.allocation_type]
#         return f"{self.winner.username} {allocation_type_display} {self.part_one_chart.user.username}的一半谱面 - {self.bid_amount}代币"
