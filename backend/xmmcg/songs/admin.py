from django.contrib import admin
from .models import (
    Song, Banner, Announcement, CompetitionPhase, 
    BiddingRound, Bid, BidResult,
    Chart, PeerReviewAllocation, PeerReview,
)


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'file_size_display', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'user__username')
    readonly_fields = ('unique_key', 'audio_hash', 'file_size', 'created_at', 'updated_at')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'title', 'unique_key')
        }),
        ('媒体文件', {
            'fields': ('audio_file', 'audio_hash', 'file_size', 'cover_image', 'background_video')
        }),
        ('链接', {
            'fields': ('netease_url',)
        }),
        ('时间戳', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        """显示文件大小（格式化）"""
        if obj.file_size:
            size_mb = obj.file_size / (1024 * 1024)
            return f'{size_mb:.2f} MB'
        return '-'
    file_size_display.short_description = '文件大小'
    
    def save_model(self, request, obj, form, change):
        """保存时自动计算file_size"""
        if obj.audio_file and not obj.file_size:
            obj.file_size = obj.audio_file.size
        
        # 如果没有audio_hash，计算它
        if obj.audio_file and not obj.audio_hash:
            from .utils import calculate_file_hash
            obj.audio_hash = calculate_file_hash(obj.audio_file)
            
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        return True


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'priority', 'created_at')
    list_filter = ('is_active', 'created_at')
    ordering = ('-priority', '-created_at')
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'content', 'button_text', 'color')
        }),
        ('链接配置', {
            'fields': ('image_url', 'link')
        }),
        ('管理', {
            'fields': ('priority', 'is_active')
        }),
    )


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_pinned', 'is_active', 'created_at')
    list_filter = ('category', 'is_pinned', 'is_active', 'created_at')
    ordering = ('-is_pinned', '-priority', '-created_at')
    search_fields = ('title', 'content')
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'category', 'content')
        }),
        ('管理', {
            'fields': ('priority', 'is_pinned', 'is_active')
        }),
    )


@admin.register(CompetitionPhase)
class CompetitionPhaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'phase_key', 'submissions_type', 'status', 'start_time', 'end_time', 'order', 'is_active')
    list_filter = ('is_active', 'submissions_type', 'start_time', 'created_at')
    ordering = ('order', 'start_time')
    search_fields = ('name', 'phase_key', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'phase_key', 'description', 'submissions_type')
        }),
        ('时间配置', {
            'fields': ('start_time', 'end_time', 'order')
        }),
        ('页面访问权限', {
            'fields': ('page_access',),
            'description': '配置该阶段允许访问的功能页面。格式: {"songs": true, "charts": false, "profile": true}。注：首页、登录、注册页总是可访问，无需配置。'
        }),
        ('管理', {
            'fields': ('is_active',)
        }),
        ('系统', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BiddingRound)
class BiddingRoundAdmin(admin.ModelAdmin):
    list_display = ('name', 'bidding_type', 'competition_phase', 'status', 'available_targets_count', 'allow_public_view', 
                    'created_at', 'started_at', 'completed_at')
    list_editable = ('status', 'allow_public_view')
    list_filter = ('bidding_type', 'status', 'created_at', 'competition_phase', 'bidding_type')
    ordering = ('-created_at',)
    search_fields = ('name',)
    actions = ['allocate_bids_action', 'auto_create_chart_round_action']
    
    def available_targets_count(self, obj):
        """显示该轮次的可用目标数量"""
        if obj.bidding_type == 'song':
            from .models import Song
            count = Song.objects.count()
        else:  # chart
            from .models import Chart
            count = Chart.objects.filter(status='part_submitted').count()
        return count
    available_targets_count.short_description = '可用目标数'
    
    @admin.action(description='分配选中的竞标轮次')
    def allocate_bids_action(self, request, queryset):
        """
        自定义管理员操作：批量分配选中的竞标轮次
        """
        from .bidding_service import BiddingService
        from django.contrib import messages
        
        success_count = 0
        error_messages = []
        
        for bidding_round in queryset:
            try:
                # 检查轮次是否已完成
                if bidding_round.status == 'completed':
                    error_messages.append(f'{bidding_round.name} 已经分配过，无法重复分配')
                    continue
                
                # 执行分配
                BiddingService.allocate_bids(bidding_round.id)
                success_count += 1
                
            except Exception as e:
                error_messages.append(f'{bidding_round.name} 分配失败: {str(e)}')
        
        # 显示结果消息
        if success_count > 0:
            self.message_user(
                request,
                f'成功分配 {success_count} 个竞标轮次',
                level=messages.SUCCESS
            )
        
        if error_messages:
            self.message_user(
                request,
                '\n'.join(error_messages),
                level=messages.WARNING
            )
    
    @admin.action(
        description='快速创建谱面竞标轮次（自动筛选半成品谱面）',
        permissions=['add']
    )
    def auto_create_chart_round_action(self, request, queryset):
        """
        快速创建谱面竞标轮次的管理员操作
        说明：该操作会自动创建一个新的谱面竞标轮次，并自动筛选所有半成品谱面作为竞标标的
        注：此 action 无需选择项目，直接点击即可创建
        """
        from django.contrib import messages
        from django.utils import timezone
        from .models import Chart
        
        # 统计半成品谱面
        half_finished = Chart.objects.filter(status='part_submitted')
        chart_count = half_finished.count()
        
        if chart_count == 0:
            self.message_user(
                request,
                '当前没有半成品谱面可竞标，无法创建谱面竞标轮次',
                level=messages.WARNING
            )
            return
        
        try:
            # 创建新的谱面竞标轮次
            new_round = BiddingRound.objects.create(
                name=f'第二轮竞标 - 谱面完成 ({timezone.now().strftime("%Y-%m-%d %H:%M")})',
                bidding_type='chart',
                status='active'
            )
            
            self.message_user(
                request,
                f'✓ 成功创建谱面竞标轮次 "{new_round.name}"',
                level=messages.SUCCESS
            )
            self.message_user(
                request,
                f'✓ 包含 {chart_count} 个半成品谱面作为竞标标的',
                level=messages.SUCCESS
            )
            
        except Exception as e:
            self.message_user(
                request,
                f'✗ 创建失败: {str(e)}',
                level=messages.ERROR
            )
    
    readonly_fields = ('created_at', 'available_targets_count')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'bidding_type', 'competition_phase')
        }),
        ('状态管理', {
            'fields': ('status',)
        }),
        ('统计信息', {
            'fields': ('available_targets_count',),
            'description': '显示该轮次可用的竞标目标数量（歌曲或谱面数）'
        }),
        ('时间信息', {
            'fields': ('started_at', 'completed_at', 'created_at')
        }),
    )
    
    def get_actions(self, request):
        """根据轮次类型动态显示操作"""
        actions = super().get_actions(request)
        # 只在列表视图中显示 auto_create_chart_round_action
        # 在编辑视图中不需要显示
        return actions


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('bidding_round', 'bid_type', 'user', 'song', 'chart', 'amount', 'is_dropped', 'created_at')
    list_filter = ('bidding_round', 'bid_type', 'is_dropped', 'created_at')
    ordering = ('-created_at',)
    search_fields = ('user__username', 'song__title', 'chart__song__title', 'chart__user__username', 'bidding_round__name')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('竞标信息', {
            'fields': ('bidding_round', 'bid_type', 'user', 'song', 'chart', 'amount', 'is_dropped')
        }),
        ('系统', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(BidResult)
class BidResultAdmin(admin.ModelAdmin):
    list_display = ('bidding_round', 'bid_type', 'song', 'chart', 'user', 'bid_amount', 'allocation_type', 'allocated_at')
    list_filter = ('bidding_round', 'bid_type', 'allocation_type', 'allocated_at')
    ordering = ('-allocated_at',)
    search_fields = ('song__title', 'chart__song__title', 'chart__user__username', 'user__username', 'bidding_round__name')
    readonly_fields = ('allocated_at',)
    
    fieldsets = (
        ('竞标结果', {
            'fields': ('bidding_round', 'bid_type', 'song', 'chart', 'user', 'bid_amount', 'allocation_type')
        }),
        ('系统', {
            'fields': ('allocated_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Chart)
class ChartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'song', 'status', 'is_part_one', 'designer', 'review_count', 'average_score', 'created_at')
    list_filter = ('status', 'is_part_one', 'bidding_round', 'created_at')
    ordering = ('-created_at',)
    search_fields = ('user__username', 'song__title', 'designer')
    readonly_fields = ('review_count', 'total_score', 'average_score', 'created_at', 'submitted_at', 'review_completed_at')
    actions = ['view_available_for_bidding']
    
    def view_available_for_bidding(self, request, queryset):
        """
        显示哪些谱面可用于竞标（status='part_submitted'）
        """
        from django.contrib import messages
        available = Chart.objects.filter(status='part_submitted')
        count = available.count()
        self.message_user(
            request,
            f'当前有 {count} 个半成品谱面可用于竞标',
            level=messages.INFO
        )
    view_available_for_bidding.short_description = '查看可竞标的谱面'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('bidding_round', 'user', 'song', 'bid_result')
        }),
        ('谱面信息', {
            'fields': ('designer', 'chart_file')
        }),
        ('媒体文件', {
            'fields': ('audio_file', 'cover_image')
        }),
        ('状态', {
            'fields': ('status', 'is_part_one', 'part_one_chart', 'completion_bid_result')
        }),
        ('评分统计', {
            'fields': ('review_count', 'total_score', 'average_score'),
            'classes': ('collapse',)
        }),
        ('时间戳', {
            'fields': ('created_at', 'submitted_at', 'review_completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PeerReviewAllocation)
class PeerReviewAllocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'reviewer', 'chart', 'status', 'allocated_at')
    list_filter = ('status', 'allocated_at')
    ordering = ('-allocated_at',)
    search_fields = ('reviewer__username', 'chart__song__title')
    readonly_fields = ('allocated_at',)
    
    fieldsets = (
        ('分配信息', {
            'fields': ('reviewer', 'chart', 'status')
        }),
        ('时间', {
            'fields': ('allocated_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PeerReview)
class PeerReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'reviewer', 'chart', 'score', 'created_at')
    list_filter = ('created_at',)
    ordering = ('-created_at',)
    search_fields = ('reviewer__username', 'chart__song__title')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('评分信息', {
            'fields': ('allocation', 'reviewer', 'chart')
        }),
        ('评分内容', {
            'fields': ('score', 'comment')
        }),
        ('时间', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


# 第二轮竞标相关Admin（已废弃）
# @admin.register(SecondBiddingRound)
# class SecondBiddingRoundAdmin(admin.ModelAdmin):
#     ...


# @admin.register(SecondBid)
# class SecondBidAdmin(admin.ModelAdmin):
#     ...


# @admin.register(SecondBidResult)
# class SecondBidResultAdmin(admin.ModelAdmin):
#     ...%