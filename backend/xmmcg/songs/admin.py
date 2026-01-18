from django.contrib import admin
from .models import (
    Song, Banner, Announcement, CompetitionPhase, 
    BiddingRound, Bid, BidResult,
    Chart, PeerReviewAllocation, PeerReview,
)


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'user__username')
    readonly_fields = ('unique_key', 'audio_hash', 'created_at', 'updated_at')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('user', 'title', 'unique_key')
        }),
        ('媒体文件', {
            'fields': ('audio_file', 'audio_hash', 'cover_image')
        }),
        ('链接', {
            'fields': ('netease_url',)
        }),
        ('时间戳', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
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
    list_display = ('name', 'bidding_type', 'competition_phase', 'status', 'created_at', 'started_at', 'completed_at')
    list_filter = ('bidding_type', 'status', 'created_at', 'competition_phase')
    ordering = ('-created_at',)
    search_fields = ('name',)
    actions = ['allocate_bids_action']
    
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
    
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'bidding_type', 'competition_phase')
        }),
        ('状态管理', {
            'fields': ('status',)
        }),
        ('时间信息', {
            'fields': ('started_at', 'completed_at', 'created_at')
        }),
    )


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
    list_display = ('id', 'user', 'song', 'status', 'is_part_one', 'review_count', 'average_score', 'created_at')
    list_filter = ('status', 'is_part_one', 'bidding_round', 'created_at')
    ordering = ('-created_at',)
    search_fields = ('user__username', 'song__title')
    readonly_fields = ('review_count', 'total_score', 'average_score', 'created_at', 'submitted_at', 'review_completed_at')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('bidding_round', 'user', 'song', 'bid_result')
        }),
        ('谱面文件', {
            'fields': ('chart_file', 'status')
        }),
        ('部分信息', {
            'fields': ('is_part_one', 'part_one_chart', 'completion_bid_result')
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
    list_display = ('id', 'bidding_round', 'reviewer', 'chart', 'status', 'allocated_at')
    list_filter = ('status', 'bidding_round', 'allocated_at')
    ordering = ('-allocated_at',)
    search_fields = ('reviewer__username', 'chart__song__title')
    readonly_fields = ('allocated_at',)
    
    fieldsets = (
        ('分配信息', {
            'fields': ('bidding_round', 'reviewer', 'chart', 'status')
        }),
        ('时间', {
            'fields': ('allocated_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PeerReview)
class PeerReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'reviewer', 'chart', 'score', 'created_at')
    list_filter = ('bidding_round', 'created_at')
    ordering = ('-created_at',)
    search_fields = ('reviewer__username', 'chart__song__title')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('评分信息', {
            'fields': ('allocation', 'bidding_round', 'reviewer', 'chart')
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
#     ...
