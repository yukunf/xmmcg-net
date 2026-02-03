from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.http import HttpResponse
from django.conf import settings
import io
import zipfile
import logging
import hashlib

from xmmcg.settings import ENABLE_CHART_FORWARD_TO_MAJDATA

logger = logging.getLogger(__name__)
import os

from .models import Song, Bid, BiddingRound, BidResult, MAX_SONGS_PER_USER, MAX_BIDS_PER_USER, Banner, Announcement, CompetitionPhase, Chart
from .serializers import (
    SongUploadSerializer,
    SongDetailSerializer,
    SongListSerializer,
    SongAnonymousSerializer,
    SongUpdateSerializer,
    BannerSerializer,
    AnnouncementSerializer,
    CompetitionPhaseSerializer,
    BidSerializer,
)
from .bidding_service import BiddingService


# ==================== 权限检查辅助函数 ====================

def get_active_phase_for_bidding(bid_type='song', phase_id=None, is_admin=False):
    """
    获取可用于竞标的活跃阶段
    
    Args:
        bid_type: 'song' 或 'chart'
        phase_id: 指定的阶段ID（可选）
        is_admin: 是否为管理员（管理员可以绕过 is_active 检查）
    
    Returns:
        CompetitionPhase 对象或 None
    
    逻辑：
        - 如果提供了 phase_id，尝试获取该阶段
        - 管理员：不检查 is_active，只要阶段存在即可
        - 普通用户：严格检查 is_active=True
    """
    phase_key_filter = 'music_bid' if bid_type == 'song' else 'chart_bid'
    
    if phase_id:
        # 指定了阶段ID
        try:
            phase = CompetitionPhase.objects.get(
                id=phase_id,
                phase_key__icontains=phase_key_filter
            )
            
            # 管理员可以操作任何阶段，普通用户只能操作 is_active=True 的阶段
            if is_admin or phase.is_active:
                return phase
            else:
                return None  # 阶段未激活且用户非管理员
                
        except CompetitionPhase.DoesNotExist:
            return None
    else:
        # 未指定阶段，查找当前活跃阶段
        # 管理员模式：查找最近的阶段（无论是否 is_active）
        # 普通用户：只查找 is_active=True 的阶段
        if is_admin:
            # 管理员：获取最新的相关阶段
            return CompetitionPhase.objects.filter(
                phase_key__icontains=phase_key_filter
            ).order_by('-start_time').first()
        else:
            # 普通用户：只获取 is_active=True 的阶段
            return CompetitionPhase.objects.filter(
                phase_key__icontains=phase_key_filter,
                is_active=True
            ).first()


def validate_phase_for_submission(phase, is_admin=False):
    """
    验证阶段是否可用于提交竞标
    
    Args:
        phase: CompetitionPhase 对象
        is_admin: 是否为管理员
    
    Returns:
        (is_valid: bool, error_message: str or None)
    """
    if phase is None:
        return False, '当前没有活跃的竞标轮次'
    
    # 管理员可以绕过所有检查
    if is_admin:
        return True, None
    
    # 普通用户：严格检查 is_active
    if not phase.is_active:
        return False, '该竞标轮次未开放或已结束'
    
    return True, None


# ==================== API 视图 ====================

@api_view(['GET'])
@permission_classes([AllowAny])
def get_banners(request):
    """获取启用的 Banner 列表"""
    banners = Banner.objects.filter(is_active=True).order_by('-priority')
    serializer = BannerSerializer(banners, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_announcements(request):
    """获取启用的公告列表（分页）"""
    limit = int(request.query_params.get('limit', 10))
    announcements = Announcement.objects.filter(is_active=True).order_by('-is_pinned', '-priority', '-created_at')[:limit]
    serializer = AnnouncementSerializer(announcements, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_competition_status(request):
    """公开的比赛状态，用于前端首页展示（从 CompetitionPhase 获取）"""
    now = timezone.now()
    
    # 获取当前活跃的阶段（不限于竞标阶段）
    current_phase = CompetitionPhase.objects.filter(
        is_active=True,
        start_time__lte=now,
        end_time__gte=now
    ).first()
    
    if not current_phase:
        # 如果没有当前活跃阶段，尝试获取最近的阶段
        current_phase = CompetitionPhase.objects.filter(
            is_active=True
        ).order_by('-start_time').first()
    
    if not current_phase:
        return Response({
            'currentRound': '未开始',
            'status': 'pending',
            'statusText': '待开始',
            'participants': 0,
            'submissions': 0,
            'peer_review_max_score': getattr(settings, 'PEER_REVIEW_MAX_SCORE', 50),
            'current_round_id': None,  # 没有活跃轮次
        }, status=status.HTTP_200_OK)
    
    # 根据时间判断状态
    if now < current_phase.start_time:
        status_val = 'pending'
        status_text = '待开始'
    elif now > current_phase.end_time:
        status_val = 'completed'
        status_text = '已完成'
    else:
        status_val = 'active'
        status_text = '进行中'
    
    # 计算参与人数（全局统计）
    total_participants = Bid.objects.values('user_id').distinct().count()
    
    # 根据阶段的 submissions_type 字段计算提交作品数
    if current_phase.submissions_type == 'songs':
        # 统计歌曲数
        submissions_count = Song.objects.count()
        submissions_label = '歌曲数'
    elif current_phase.submissions_type == 'charts':
        # 统计谱面数
        from .models import Chart
        submissions_count = Chart.objects.count()
        submissions_label = '谱面数'
    else:
        # 其他阶段：默认统计歌曲数
        submissions_count = Song.objects.count()
        submissions_label = '作品数'

    return Response({
        'currentRound': current_phase.name,
        'status': status_val,
        'statusText': status_text,
        'participants': total_participants,
        'submissions': submissions_count,
        'submissionsLabel': submissions_label,  # 新增：提交作品数的标签
        'phaseKey': current_phase.phase_key,
        'startTime': current_phase.start_time,
        'endTime': current_phase.end_time,
        'peer_review_max_score': getattr(settings, 'PEER_REVIEW_MAX_SCORE', 50),  # 互评最大分数
        'current_round_id': current_phase.id,  # 当前轮次ID
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_competition_phases(request):
    """获取所有比赛阶段信息
    
    查询参数:
        include_inactive: 'true' 时返回所有阶段（包括 is_active=False 的），
                         否则只返回 is_active=True 的阶段（默认行为）
    """
    include_inactive = request.GET.get('include_inactive', 'false').lower() == 'true'
    
    if include_inactive:
        phases = CompetitionPhase.objects.all().order_by('order')
    else:
        phases = CompetitionPhase.objects.filter(is_active=True).order_by('order')
    
    serializer = CompetitionPhaseSerializer(phases, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)




@api_view(['GET'])
@permission_classes([AllowAny])
def get_current_phase(request):
    """获取当前活跃的比赛阶段及权限信息"""
    now = timezone.now()
    
    # 获取当前进行中的阶段
    current_phase = CompetitionPhase.objects.filter(
        is_active=True,
        start_time__lte=now,
        end_time__gte=now
    ).first()
    
    if current_phase:
        serializer = CompetitionPhaseSerializer(current_phase)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        # 如果没有进行中的阶段，返回下一个即将开始的阶段
        next_phase = CompetitionPhase.objects.filter(
            is_active=True,
            start_time__gt=now
        ).order_by('start_time').first()
        
        if next_phase:
            serializer = CompetitionPhaseSerializer(next_phase)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # 都没有，返回最后一个阶段
            last_phase = CompetitionPhase.objects.filter(
                is_active=True
            ).order_by('-end_time').first()
            
            if last_phase:
                serializer = CompetitionPhaseSerializer(last_phase)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': '暂无比赛阶段信息'
                }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_announcements_old(request):
    data = [
        {
            'title': '平台上线公告',
            'content': '<p>欢迎来到 XMMCG 谱面创作竞赛平台！</p>',
            'time': timezone.now().strftime('%Y-%m-%d %H:%M'),
            'type': 'success',
        },
    ]
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def songs_root(request):
    """
    根路径处理：
    GET /api/songs/ - 列出所有歌曲（任何人）
    POST /api/songs/ - 上传歌曲（需要认证）
    """
    if request.method == 'GET':
        # 列出所有歌曲
        songs = Song.objects.all()
        # 分页处理
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = songs.count()
        songs_page = songs[start:end]
        
        serializer = SongAnonymousSerializer(songs_page, many=True)
        
        return Response({
            'success': True,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    else:  # POST - 上传歌曲
        # 检查认证
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': '需要认证'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        user = request.user
        
        # 检查用户是否达到上传限制
        song_count = Song.objects.filter(user=user).count()
        if song_count >= MAX_SONGS_PER_USER:
            return Response({
                'success': False,
                'message': f'已达到每个用户最多 {MAX_SONGS_PER_USER} 首歌曲的限制',
                'current_count': song_count,
                'limit': MAX_SONGS_PER_USER
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 序列化并验证数据
        serializer = SongUploadSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            song = serializer.save()
            return Response({
                'success': True,
                'message': '歌曲上传成功',
                'song': SongDetailSerializer(song).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_songs(request):
    """
    获取当前用户上传的所有歌曲
    GET /api/songs/me/
    
    权限: 需要认证
    返回用户上传的所有歌曲列表
    """
    user = request.user
    songs = Song.objects.filter(user=user).order_by('-created_at')
    
    if not songs.exists():
        return Response({
            'success': True,
            'message': '您尚未上传过歌曲',
            'songs': []
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': True,
        'count': songs.count(),
        'songs': SongDetailSerializer(songs, many=True).data
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_my_song(request, song_id=None):
    """
    更新当前用户的歌曲信息
    PUT/PATCH /api/songs/{song_id}/update/ 或 /api/songs/me/{song_id}/
    
    权限: 需要认证
    可更新字段: title, netease_url
    """
    user = request.user
    
    # 获取指定的歌曲
    try:
        if song_id:
            song = Song.objects.get(id=song_id, user=user)
        else:
            # 如果没有指定ID，获取用户的最新歌曲（向后兼容）
            song = Song.objects.filter(user=user).latest('-id')
    except Song.DoesNotExist:
        return Response({
            'success': False,
            'message': '您尚未上传过该歌曲或无权编辑'
        }, status=status.HTTP_404_NOT_FOUND)
    
    serializer = SongUpdateSerializer(song, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'success': True,
            'message': '歌曲信息已更新',
            'song': SongDetailSerializer(song).data
        }, status=status.HTTP_200_OK)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_my_song(request, song_id=None):
    """
    删除当前用户的指定歌曲
    DELETE /api/songs/{song_id}/ 或 DELETE /api/songs/me/{song_id}/
    
    权限: 需要认证
    删除后可重新上传新歌曲（如未达到限制）
    """
    user = request.user
    
    try:
        if song_id:
            song = Song.objects.get(id=song_id, user=user)
        else:
            # 如果没有指定ID，删除用户的最新歌曲（向后兼容）
            song = Song.objects.filter(user=user).latest('-id')
    except Song.DoesNotExist:
        return Response({
            'success': False,
            'message': '歌曲不存在或无权删除'
        }, status=status.HTTP_404_NOT_FOUND)
    
    song_id_val = song.id
    song_title = song.title
    song.delete()
    
    return Response({
        'success': True,
        'message': '歌曲已删除',
        'deleted_song': {
            'id': song_id_val,
            'title': song_title
        }
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_song_detail(request, song_id):
    """
    获取特定歌曲的详情
    GET /api/songs/{id}/
    
    权限: 任何人
    用途: 竞标前查看详情
    """
    song = get_object_or_404(Song, id=song_id)
    
    return Response({
        'success': True,
        'song': SongDetailSerializer(song).data
    }, status=status.HTTP_200_OK)


# ==================== 竞标相关 API ====================

@api_view(['GET'])
@permission_classes([AllowAny])
def bidding_rounds_root(request):
    """
    竞标轮次管理
    GET /api/bidding-rounds/ - 列出所有竞标轮次（从 BiddingRound 表获取）
    """
    # 直接从 BiddingRound 表获取所有轮次
    bidding_rounds = BiddingRound.objects.all().order_by('-created_at')
    
    data = []
    for round_obj in bidding_rounds:
        data.append({
            'id': round_obj.id,
            'name': round_obj.name,
            'bidding_type': round_obj.bidding_type,
            'status': round_obj.status,
            'status_display': round_obj.get_status_display(),
            'created_at': round_obj.created_at,
            'started_at': round_obj.started_at,
            'completed_at': round_obj.completed_at,
        })
    
    return Response({
        'success': True,
        'count': len(data),
        'rounds': data
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_bids_root(request):
    """
    用户竞标管理
    GET /api/bids/ - 获取当前用户在活跃竞标轮次的竞标
    POST /api/bids/ - 创建新的竞标
    """
    user = request.user
    
    if request.method == 'GET':
        # 获取活跃的竞标轮次
        round_id = request.query_params.get('round_id')
        is_admin = request.user.is_authenticated and request.user.is_staff
        
        round_obj = None
        
        if round_id:
            # 尝试直接通过 BiddingRound ID 获取
            try:
                round_obj = BiddingRound.objects.get(id=round_id, bidding_type='song')
            except BiddingRound.DoesNotExist:
                # 如果不是 BiddingRound ID，尝试作为 CompetitionPhase ID
                phase = get_active_phase_for_bidding(
                    bid_type='song',
                    phase_id=round_id,
                    is_admin=is_admin
                )
                if phase:
                    round_obj = phase.bidding_rounds.filter(bidding_type='song').first()
                    if not round_obj:
                        round_obj = BiddingRound.objects.create(
                            competition_phase=phase,
                            bidding_type='song',
                            name=phase.name,
                            status='active'
                        )
        else:
            # 未指定 ID，使用辅助函数获取活跃阶段
            phase = get_active_phase_for_bidding(
                bid_type='song',
                phase_id=None,
                is_admin=is_admin
            )
            if phase:
                round_obj = phase.bidding_rounds.filter(bidding_type='song').first()
                if not round_obj:
                    round_obj = BiddingRound.objects.create(
                        competition_phase=phase,
                        bidding_type='song',
                        name=phase.name,
                        status='active'
                    )
        
        if not round_obj:
            return Response({
                'success': True,
                'message': '当前没有活跃的竞标轮次',
                'bids': [],
                'bid_count': 0,
                'max_bids': MAX_BIDS_PER_USER,
            }, status=status.HTTP_200_OK)
        
        # 获取用户在该轮次的所有竞标
        bids = Bid.objects.filter(
            bidding_round=round_obj,
            user=user
        ).select_related('song').order_by('-amount')
        
        # 使用序列化器以包含 status 字段
        bids_data = BidSerializer(bids, many=True).data
        
        return Response({
            'success': True,
            'round': {
                'id': round_obj.id,
                'name': round_obj.name,
                'status': round_obj.status,
            },
            'bid_count': bids.count(),
            'max_bids': MAX_BIDS_PER_USER,
            'bids': bids_data
        }, status=status.HTTP_200_OK)
    
    else:  # POST - 创建竞标（支持歌曲和谱面）
        song_id = request.data.get('song_id')
        chart_id = request.data.get('chart_id')
        amount = request.data.get('amount')
        round_id = request.data.get('round_id')
        
        # 验证必须提供song_id或chart_id，二选一
        if not (song_id or chart_id) or amount is None:
            return Response({
                'success': False,
                'message': '缺少必要字段：(song_id或chart_id), amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if song_id and chart_id:
            return Response({
                'success': False,
                'message': '不能同时竞标歌曲和谱面'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取竞标目标
        song = None
        chart = None
        if song_id:
            try:
                song = Song.objects.get(id=song_id)
            except Song.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '歌曲不存在'
                }, status=status.HTTP_404_NOT_FOUND)
        else:  # chart_id
            try:
                chart = Chart.objects.get(id=chart_id)
            except Chart.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '谱面不存在'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # 获取竞标轮次（支持 CompetitionPhase ID 或 BiddingRound ID）
        bid_type = 'song' if song else 'chart'
        is_admin = request.user.is_staff
        
        round_obj = None
        phase = None
        
        if round_id:
            # 尝试直接通过 BiddingRound ID 获取
            try:
                round_obj = BiddingRound.objects.get(id=round_id, bidding_type=bid_type)
                phase = round_obj.competition_phase
            except BiddingRound.DoesNotExist:
                # 如果不是 BiddingRound ID，尝试作为 CompetitionPhase ID
                phase = get_active_phase_for_bidding(
                    bid_type=bid_type,
                    phase_id=round_id,
                    is_admin=is_admin
                )
                if phase:
                    round_obj = phase.bidding_rounds.filter(bidding_type=bid_type).first()
                    if not round_obj:
                        round_obj = BiddingRound.objects.create(
                            competition_phase=phase,
                            bidding_type=bid_type,
                            name=phase.name,
                            status='active'
                        )
        else:
            # 未指定 ID，使用辅助函数获取活跃阶段
            phase = get_active_phase_for_bidding(
                bid_type=bid_type,
                phase_id=None,
                is_admin=is_admin
            )
            if phase:
                round_obj = phase.bidding_rounds.filter(bidding_type=bid_type).first()
                if not round_obj:
                    round_obj = BiddingRound.objects.create(
                        competition_phase=phase,
                        bidding_type=bid_type,
                        name=phase.name,
                        status='active'
                    )
        
        # 验证阶段是否可用于提交
        is_valid, error_message = validate_phase_for_submission(phase, is_admin)
        if not is_valid:
            return Response({
                'success': False,
                'message': error_message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not round_obj:
            return Response({
                'success': False,
                'message': '当前没有活跃的竞标轮次'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            amount = int(amount)
            bid = BiddingService.create_bid(user, round_obj, amount, song=song, chart=chart)
            
            # 构建响应数据
            target_data = SongListSerializer(song).data if song else {
                'id': chart.id,
                'title': chart.song.title,
                'creator': chart.user.username
            }
            
            return Response({
                'success': True,
                'message': '竞标已创建',
                'bid': {
                    'id': bid.id,
                    'bid_type': bid.bid_type,
                    'target': target_data,
                    'amount': bid.amount,
                    'created_at': bid.created_at,
                }
            }, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response({
                'success': False,
                'message': str(e.message) if hasattr(e, 'message') else str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
            
from .models import BiddingRound, CompetitionPhase, Bid, Song, Chart 
# 如果有 User Serializer 可以导入，或者使用下面定义的简单 Serializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def target_bids_list(request):
    """
    获取特定目标（歌曲/谱面）在特定轮次的所有竞标记录（行情列表）
    GET /api/bids/target/?song_id=1&round_id=5
    GET /api/bids/target/?chart_id=2&round_id=5
    """
    song_id = request.query_params.get('song_id')
    chart_id = request.query_params.get('chart_id')
    round_id = request.query_params.get('round_id')

    # 1. 参数验证：必须指定 song_id 或 chart_id 之一
    if not (song_id or chart_id):
        return Response({'success': False, 'message': '必须提供 song_id 或 chart_id'}, status=status.HTTP_400_BAD_REQUEST)
    
    if song_id and chart_id:
        return Response({'success': False, 'message': '无法同时查询歌曲和谱面'}, status=status.HTTP_400_BAD_REQUEST)

    # 2. 获取竞标轮次 (BiddingRound)
    # 逻辑简化：如果没传 round_id，自动找当前活跃的。
    # 既然是查行情，通常不涉及创建轮次，只查存在的。
    round_obj = None
    
    if round_id:
        # 优先尝试直接获取 BiddingRound
        try:
            round_obj = BiddingRound.objects.get(id=round_id)
        except BiddingRound.DoesNotExist:
            # 尝试通过 Phase ID 获取
            try:
                b_type = 'song' if song_id else 'chart'
                phase_key_filter = 'music_bid' if b_type == 'song' else 'chart_bid'
                
                phase = CompetitionPhase.objects.get(
                    id=round_id,
                    phase_key__icontains=phase_key_filter
                )
                round_obj = phase.bidding_rounds.filter(bidding_type=b_type).first()
            except CompetitionPhase.DoesNotExist:
                return Response({'success': False, 'message': '轮次不存在'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # 未指定轮次，查找当前活跃轮次
        now = timezone.now()
        b_type = 'song' if song_id else 'chart'
        phase_key_filter = 'music_bid' if b_type == 'song' else 'chart_bid'
        
        active_phase = CompetitionPhase.objects.filter(
            phase_key__icontains=phase_key_filter,
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        ).first()

        if active_phase:
            round_obj = active_phase.bidding_rounds.filter(bidding_type=b_type).first()

    if not round_obj:
        return Response({
            'success': True, 
            'message': '当前没有活跃的竞标轮次', 
            'results': []
        }, status=status.HTTP_200_OK)
        

    # 3. 验证目标是否存在 (可选，但为了严谨性建议加上)
    target_title = ""
    if song_id:
        song = get_object_or_404(Song, id=song_id)
        target_title = song.title
    elif chart_id:
        chart = get_object_or_404(Chart, id=chart_id)
        target_title = f"{chart.song.title} ({chart.user.username})"

    # 4. 查询所有竞标
    # 注意：这里我们获取该目标的 *所有* 有效竞标
    bids_qs = Bid.objects.filter(
        bidding_round=round_obj,
        is_dropped=False  # 通常看行情只看有效的，如果需要看历史记录可以去掉这个
    )

    if song_id:
        bids_qs = bids_qs.filter(song_id=song_id)
    else:
        bids_qs = bids_qs.filter(chart_id=chart_id)

    # 排序：金额降序，时间升序（先出价的排前面）
    bids_qs = bids_qs.order_by('-amount', 'created_at').select_related('user')

    # 5. 手动序列化 (比用 Serializer 更灵活，且只需返回前端需要的字段)
    results = []
    current_user = request.user

    for bid in bids_qs:
        
        raw_username = bid.user.username
        hash_obj = hashlib.md5(raw_username.encode('utf-8'))
        anonymous_name = hash_obj.hexdigest()[:6].upper()
        if not round_obj.allow_public_view and not request.user.is_staff:
            #若不许访问在这里抹去竞价价格
            results.append({
            'id': bid.id,
            'amount': 114514,
            'username': anonymous_name,  # 显示匿名用户名
            # 'user_id': bid.user.id,       # 如果需要点击跳转用户主页
            'created_at': bid.created_at,
            'is_self': bid.user == current_user,  # 关键字段：是否是当前用户
            'is_dropped': bid.is_dropped
        })

        else:
            results.append({
                'id': bid.id,
                'amount': bid.amount,
                'username': anonymous_name,  # 显示匿名用户名
                # 'user_id': bid.user.id,       # 如果需要点击跳转用户主页
                'created_at': bid.created_at,
                'is_self': bid.user == current_user,  # 关键字段：是否是当前用户
                'is_dropped': bid.is_dropped
            })

    return Response({
        'success': True,
        'round': {
            'id': round_obj.id,
            'name': round_obj.name,
            'status': round_obj.status
        },
        'target': {
            'id': song_id or chart_id,
            'type': 'song' if song_id else 'chart',
            'title': target_title
        },
        'count': len(results),
        'results': results
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_bid_view(request, bid_id):
    """
    删除用户的竞标
    DELETE /api/songs/bids/{bid_id}/
    
    只允许删除未完成的竞标轮次中的竞标（status='active' 或 'bidding'）
    用户只能删除自己的竞标
    """
    user = request.user
    
    try:
        bid = Bid.objects.get(id=bid_id)
    except Bid.DoesNotExist:
        return Response({
            'success': False,
            'message': '竞标不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 检查权限：只能删除自己的竞标
    if bid.user != user:
        return Response({
            'success': False,
            'message': '没有权限删除他人的竞标'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # 检查竞标轮次是否未完成
    if bid.bidding_round.status == 'completed':
        return Response({
            'success': False,
            'message': '竞标轮次已完成，无法撤回'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 删除竞标
    bid.delete()
    
    return Response({
        'success': True,
        'message': '竞标已撤回'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def allocate_bids_view(request):
    """
    执行竞标分配（Admin only）
    POST /api/bids/allocate/
    
    参数: round_id（可选，不提供则分配最新的活跃轮次）
    
    算法：
    1. 按竞标金额从高到低排序
    2. 依次为每个竞标分配歌曲
    3. 同一歌曲的其他竞标标记为 drop
    4. 对于未获得歌曲的用户，从未被分配的歌曲中随机分配
    """
    
    # 验证 admin 权限
    if not request.user.is_authenticated or not request.user.is_staff:
        return Response({
            'success': False,
            'message': '需要管理员权限'
        }, status=status.HTTP_403_FORBIDDEN)
    
    round_id = request.data.get('round_id')
    
    try:
        if round_id:
            try:
                round_obj = BiddingRound.objects.get(id=round_id)
            except BiddingRound.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '竞标轮次不存在'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            round_obj = BiddingRound.objects.filter(status='active').first()
            if not round_obj:
                return Response({
                    'success': False,
                    'message': '当前没有活跃的竞标轮次'
                }, status=status.HTTP_404_NOT_FOUND)
        
        result = BiddingService.allocate_bids(round_obj.id, priority_self=True)
        
        return Response({
            'success': True,
            'message': '竞标分配完成',
            'round': {
                'id': round_obj.id,
                'name': round_obj.name,
                'status': 'completed',
            },
            'statistics': result
        }, status=status.HTTP_200_OK)
    
    except ValidationError as e:
        return Response({
            'success': False,
            'message': str(e.message) if hasattr(e, 'message') else str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_charts_for_round(request, round_id):
    """
    获取指定竞标轮次可竞标的谱面列表
    GET /api/bidding-rounds/{round_id}/available-charts/
    
    仅对谱面类型的竞标轮次有效，返回所有 status='part_submitted' 的谱面
    """
    try:
        round_obj = BiddingRound.objects.get(id=round_id)
    except BiddingRound.DoesNotExist:
        return Response({
            'success': False,
            'message': '竞标轮次不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 仅对谱面竞标轮次有效
    if round_obj.bidding_type != 'chart':
        return Response({
            'success': False,
            'message': '该轮次不是谱面竞标，无可用谱面'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from .models import Chart
    from .serializers import ChartSerializer
    
    # 获取所有半成品谱面
    charts = Chart.objects.filter(
        status='part_submitted'
    ).select_related('song', 'user').order_by('-created_at')
    
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    
    total_count = charts.count()
    charts_page = charts[start:end]
    
    serializer = ChartSerializer(charts_page, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'round': {
            'id': round_obj.id,
            'name': round_obj.name,
            'bidding_type': round_obj.bidding_type,
        },
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size,
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_create_chart_bidding_round(request):
    """
    自动创建谱面竞标轮次并将所有半成品谱面作为竞标标的
    POST /api/bidding-rounds/auto-create-chart-round/
    
    Admin Only
    请求体:
    {
        'name': '第二轮竞标 - 谱面完成',
        'phase_id': 3  (可选)
    }
    
    实现逻辑：
    1. 创建新的 BiddingRound，bidding_type='chart'，status='active'
    2. 查询所有 status='part_submitted' 的谱面作为可竞标的标的
    3. 返回创建结果和可竞标的谱面数量
    
    说明：
    - 当用户进行竞标时，他们竞标的是这些半成品谱面
    - Admin 分配竞标时，系统自动匹配用户与对应谱面
    - 分配完成后，中标用户可见他们需要完成的谱面
    """
    # 验证 admin 权限
    if not request.user.is_authenticated or not request.user.is_staff:
        return Response({
            'success': False,
            'message': '需要管理员权限'
        }, status=status.HTTP_403_FORBIDDEN)
    
    name = request.data.get('name')
    phase_id = request.data.get('phase_id')
    
    if not name:
        return Response({
            'success': False,
            'message': '缺少竞标轮次名称'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from .models import Chart
    from django.db import transaction
    
    try:
        with transaction.atomic():
            # 1. 创建新的谱面竞标轮次
            phase_obj = None
            if phase_id:
                try:
                    phase_obj = CompetitionPhase.objects.get(id=phase_id)
                except CompetitionPhase.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': '指定的比赛阶段不存在'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            round_obj = BiddingRound.objects.create(
                name=name,
                bidding_type='chart',
                status='active',
                competition_phase=phase_obj
            )
            
            # 2. 获取所有半成品谱面（status='part_submitted'）
            half_finished_charts = Chart.objects.filter(
                status='part_submitted'
            ).select_related('song')
            
            chart_count = half_finished_charts.count()
            
            if chart_count == 0:
                # 如果没有半成品谱面，删除刚创建的轮次并返回错误
                round_obj.delete()
                return Response({
                    'success': False,
                    'message': '当前没有半成品谱面可竞标'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'message': f'成功创建谱面竞标轮次，包含 {chart_count} 个半成品谱面',
                'round': {
                    'id': round_obj.id,
                    'name': round_obj.name,
                    'bidding_type': round_obj.bidding_type,
                    'status': round_obj.status,
                },
                'available_charts_count': chart_count
            }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response({
            'success': False,
            'message': f'创建竞标轮次失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
# 已测试过匿名性
def bid_results_view(request):
    """
    获取竞标分配结果
    GET /api/bid-results/?round_id=1
    
    参数: round_id（可选）
    """
    user = request.user
    round_id = request.query_params.get('round_id')
    
    if round_id:
        try:
            round_obj = BiddingRound.objects.get(id=round_id)
        except BiddingRound.DoesNotExist:
            return Response({
                'success': False,
                'message': '竞标轮次不存在'
            }, status=status.HTTP_404_NOT_FOUND)
    else:
        # 获取最新的已完成竞标轮次
        round_obj = BiddingRound.objects.filter(status='completed').first()
        if not round_obj:
            return Response({
                'success': True,
                'message': '当前没有已完成的竞标轮次',
                'results': []
            }, status=status.HTTP_200_OK)
    
    # 获取用户的分配结果
    results = BidResult.objects.filter(
        bidding_round=round_obj,
        user=user
    ).select_related('song', 'chart', 'chart__user', 'chart__song').order_by('-bid_amount')
    
    results_data = []
    for result in results:
        item = {
            'id': result.id,
            'bid_type': result.bid_type,
            'bid_type_display': result.get_bid_type_display(),
            'bid_amount': result.bid_amount,
            'allocation_type': result.allocation_type,
            'allocation_type_display': dict(BidResult.ALLOCATION_TYPE_CHOICES)[result.allocation_type],
            'allocated_at': result.allocated_at,
        }
        if result.bid_type == 'song' and result.song:
            item['song'] = SongListSerializer(result.song).data
        elif result.bid_type == 'chart' and result.chart:
            item['chart'] = {
                'id': result.chart.id,
                "user_id": result.chart.user.id,
                'song_title': result.chart.song.title,
                'creator_username': result.chart.user.username,
                'average_score': result.chart.average_score,
            }
        results_data.append(item)
    
    return Response({
        'success': True,
        'round': {
            'id': round_obj.id,
            'name': round_obj.name,
            'status': round_obj.status,
            'completed_at': round_obj.completed_at,
        },
        'result_count': results.count(),
        'results': results_data
    }, status=status.HTTP_200_OK)


# ==================== 谱面相关API ====================

@api_view(['GET'])
@permission_classes([AllowAny])
def charts_root(request):
    """
    谱面列表
    GET /api/charts/
    """
    from .models import Chart
    from .serializers import ChartSerializer,ChartAnonymousSerializer

    charts = Chart.objects.select_related('song', 'user').order_by('-created_at')

    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    start = (page - 1) * page_size
    end = start + page_size

    total_count = charts.count()
    charts_page = charts[start:end]

    serializer = ChartAnonymousSerializer(charts_page, many=True, context={'request': request})

    return Response({
        'success': True,
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size,
        'results': serializer.data
    }, status=status.HTTP_200_OK)

MAJNET_BASE_URL = "https://majdata.net/api3/api/"
MAJNET_LOGIN_URL = "https://majdata.net/api3/api/account/Login"
MAJNET_UPLOAD_URL = "https://majdata.net/api3/api/maichart/upload"

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_chart(request, result_id):
    """
    提交谱面
    POST /api/charts/{result_id}/submit/
    
    需要参数:
    - designer (谱师名义，必填)
    - chart_file (maidata.txt)
    
    用户通过竞标获得了歌曲后，可以提交谱面
    
    阶段控制：
    - 管理员：无限制
    - 普通用户：必须在 mapping1 或 mapping2 阶段（is_active=True）
    """
    from .models import BidResult, Chart
    from .serializers import ChartCreateSerializer, ChartSerializer
    
    user = request.user
    is_admin = user.is_staff
    
    # 验证BidResult存在且属于当前用户
    bid_result = get_object_or_404(BidResult, id=result_id, user=user)
    
    # 阶段验证（管理员可绕过）
    if not is_admin:
        now = timezone.now()
        active_mapping_phase = CompetitionPhase.objects.filter(
            phase_key__in=['mapping1', 'mapping2', 'chart_mapping'],
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        ).first()
        
        if not active_mapping_phase:
            return Response({
                'success': False,
                'message': '当前不在谱面创作阶段，无法提交谱面'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # 计算目标歌曲（第一阶段：bid_result.song；第二阶段：bid_result.chart.song）
    song_target = bid_result.song if bid_result.bid_type == 'song' else (bid_result.chart.song if bid_result.chart else None)
    
    # 检查是否已有谱面（禁止覆盖上传）
    if bid_result.bid_type == 'song':
        existing_chart = Chart.objects.filter(
            user=user,
            song=song_target,
            bidding_round=bid_result.bidding_round,
            is_part_one=True
        ).first()
        if existing_chart:
            return Response({
                'success': False,
                'message': '您已提交过第一阶段的半成品谱面，无法重复上传',
                'errors': {'chart_file': ['已提交过第一阶段谱面']}
            }, status=status.HTTP_400_BAD_REQUEST)
        chart = None
    else:
        # 第二阶段：查找是否已有续写谱面（非第一部分），按completion_bid_result匹配
        existing_chart = Chart.objects.filter(
            user=user,
            bidding_round=bid_result.bidding_round,
            song=song_target,
            is_part_one=False,
            completion_bid_result=bid_result
        ).first()
        if existing_chart:
            return Response({
                'success': False,
                'message': '您已提交过第二阶段的完成稿，无法重复上传',
                'errors': {'chart_file': ['已提交过第二阶段谱面']}
            }, status=status.HTTP_400_BAD_REQUEST)
        chart = None
    
    # 处理请求数据
    serializer = ChartCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    validated = serializer.validated_data
    new_file = validated.get('chart_file')
    designer = validated.get('designer')
    new_audio = validated.get('audio_file')
    new_cover = validated.get('cover_image')
    new_video = validated.get('background_video')
    
    # 根据竞标类型自动判断应该设置的状态
    # bid_type='song': 歌曲竞标 → 提交半成品
    # bid_type='chart': 谱面竞标 → 提交完成稿
    if bid_result.bid_type == 'song':
        target_status = 'part_submitted'
        status_msg = '半成品'
    elif bid_result.bid_type == 'chart':
        target_status = 'final_submitted'
        status_msg = '完成稿'
    else:
        # 默认为半成品（兼容性）
        target_status = 'part_submitted'
        status_msg = '半成品'
    
    # 创建新谱面（已在上方检查过不存在）
    if bid_result.bid_type == 'song':
        # 第一阶段：创建半成品谱面（第一部分）
        chart = Chart.objects.create(
            bidding_round=bid_result.bidding_round,
            user=user,
            song=song_target,
            bid_result=bid_result,
            status=target_status,
            designer=designer,
            audio_file=new_audio,
            cover_image=new_cover,
            background_video=new_video,
            chart_file=new_file,
            submitted_at=timezone.now(),
            is_part_one=True
        )
    else:
        # 第二阶段：创建续写谱面（第二部分），指向第一部分谱面
        base_chart = bid_result.chart
        chart = Chart.objects.create(
            bidding_round=bid_result.bidding_round,
            user=user,
            song=song_target,
            status=target_status,
            designer=designer,
            audio_file=new_audio,
            cover_image=new_cover,
            background_video=new_video,
            chart_file=new_file,
            submitted_at=timezone.now(),
            is_part_one=False,
            part_one_chart=base_chart,
            completion_bid_result=bid_result
        )

    if  ENABLE_CHART_FORWARD_TO_MAJDATA:
        # 上传谱面到 Majdata.net
        from .majdata_service import MajdataService
        
        try:
            # 准备上传数据
            logger.info(f"准备上传谱面到 Majdata.net: Chart ID={chart.id}")
            logger.info(f"  环境: DEBUG={settings.DEBUG}, MEDIA_ROOT={settings.MEDIA_ROOT}")
            
            maidata_content = ''
            if chart.chart_file:
                # 兼容两种文件类型：UploadedFile（本地）和 FileField（远程）
                if hasattr(chart.chart_file, 'path'):
                    # FileField: 已保存到磁盘，从物理路径读取
                    logger.info(f"  读取 maidata（FileField）: {chart.chart_file.path}")
                    with open(chart.chart_file.path, 'r', encoding='utf-8') as f:
                        maidata_content = f.read()
                else:
                    # UploadedFile: 在内存中，直接读取
                    logger.info(f"  读取 maidata（UploadedFile）")
                    chart.chart_file.seek(0)
                    maidata_content = chart.chart_file.read()
                    if isinstance(maidata_content, bytes):
                        maidata_content = maidata_content.decode('utf-8')
            
            upload_data = {
                'maidata_content': maidata_content,
                'audio_file': chart.audio_file if chart.audio_file else None,
                'cover_file': chart.cover_image if chart.cover_image else (chart.song.cover_image if hasattr(chart.song, 'cover_image') else None),
                'video_file': chart.background_video if chart.background_video else None,
                'is_part_chart': (chart.is_part_one),
                'folder_name': f"{chart.song.title}_{chart.user.username}" if chart.song else f"Chart_{chart.id}"
            }
            
            logger.info(f"  maidata 长度: {len(maidata_content)} chars")
            logger.info(f"  audio_file: {upload_data['audio_file'].name if upload_data['audio_file'] else 'None'}")
            logger.info(f"  cover_file: {upload_data['cover_file'].name if upload_data['cover_file'] else 'None'}")
            logger.info(f"  video_file: {upload_data['video_file'].name if upload_data['video_file'] else 'None'}")
            logger.info(f"  is_part_chart (chart.is_part_one): {upload_data['is_part_chart']}")
            
            # 检查 maidata 中的标题内容
            title_lines = [line for line in maidata_content.split('\n') if '&title=' in line]
            if title_lines:
                logger.info(f"  当前标题行: {title_lines[0]}")
            
            upload_result = MajdataService.upload_chart(upload_data)
            
            if upload_result:
                # 保存 Majdata.net 返回的 URL（如果有）
                if isinstance(upload_result, dict):
                    external_url = upload_result.get('url') or upload_result.get('chart_url') or upload_result.get('message', '')
                    # 可以保存到 chart 对象的某个字段（需要在模型中添加）
                    # chart.majdata_url = external_url
                    # chart.save()
                    logger.info(f"✅ 谱面已上传到 Majdata.net: {external_url}")
            else:
                logger.warning(f"⚠️ 谱面上传到 Majdata.net 失败，但本地保存成功")
        
        except Exception as e:
            logger.error(f"上传到 Majdata.net 时发生错误: {e}")
            # 不影响本地保存，继续返回成功
    
    
    result_serializer = ChartSerializer(chart, context={'request': request})
    return Response({
        'success': True,
        'message': f'谱面提交成功（{status_msg}）',
        'chart': result_serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def download_chart_bundle(request, chart_id):
    """
    服务器端打包并下载谱面资源（音频、封面、视频、maidata.txt）。
    GET /api/songs/charts/{chart_id}/bundle/
    """
    chart = get_object_or_404(Chart.objects.select_related('song', 'user'), id=chart_id)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 谱面文件
        if chart.chart_file and chart.chart_file.storage.exists(chart.chart_file.name):
            with chart.chart_file.open('rb') as f:
                zf.writestr('maidata.txt', f.read())

        # 音频
        if chart.audio_file and chart.audio_file.storage.exists(chart.audio_file.name):
            audio_ext = os.path.splitext(chart.audio_file.name)[1].lower() or '.mp3'
            with chart.audio_file.open('rb') as f:
                zf.writestr(f'track{audio_ext}', f.read())

        # 封面
        if chart.cover_image and chart.cover_image.storage.exists(chart.cover_image.name):
            cover_ext = os.path.splitext(chart.cover_image.name)[1].lower() or '.jpg'
            with chart.cover_image.open('rb') as f:
                zf.writestr(f'bg{cover_ext}', f.read())

        # 视频（可选）
        if chart.background_video and chart.background_video.storage.exists(chart.background_video.name):
            # 文件名包含 bg/pv 时按名称命名，否则默认 bg.mp4
            basename = os.path.basename(chart.background_video.name).lower()
            target_name = 'bg.mp4'
            if basename.startswith('pv') or 'pv.' in basename:
                target_name = 'pv.mp4'
            elif basename.endswith('.mp4'):
                target_name = 'bg.mp4'
            else:
                # 保留原扩展名
                target_name = 'bg' + os.path.splitext(basename)[1].lower()
            with chart.background_video.open('rb') as f:
                zf.writestr(target_name, f.read())

    buffer.seek(0)

    # 安全文件名
    def sanitize_filename(name: str) -> str:
        return (name or 'chart').replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_') \
            .replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_').strip() or 'chart'

    filename = f"{sanitize_filename(chart.song.title)}_chart.zip"
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    # 提供范围与长度信息（有助于某些下载器）
    response['Accept-Ranges'] = 'bytes'
    response['Content-Length'] = str(len(buffer.getvalue()))
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_charts(request):
    """
    获取当前用户的所有谱面
    GET /api/charts/me/
    """
    from .models import Chart
    from .serializers import ChartSerializer
    
    user = request.user
    
    # 获取参数
    bidding_round_id = request.query_params.get('bidding_round_id')
    
    charts = Chart.objects.filter(user=user)
    
    if bidding_round_id:
        charts = charts.filter(bidding_round_id=bidding_round_id)
    
    charts = charts.select_related('song', 'bidding_round').order_by('-created_at')
    
    serializer = ChartSerializer(charts, many=True, context={'request': request})
    
    return Response({
        'success': True,
        'count': charts.count(),
        'charts': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def allocate_peer_reviews(request, round_id):
    """
    分配互评任务（管理员操作）
    POST /api/peer-reviews/allocate/{round_id}/
    
    参数:
    - reviews_per_user: 每个用户的评分任务数（默认8）
    """
    from .bidding_service import PeerReviewService
    
    # 可选：检查是否为管理员
    # if not request.user.is_staff:
    #     return Response({
    #         'success': False,
    #         'message': '只有管理员可以分配互评任务'
    #     }, status=status.HTTP_403_FORBIDDEN)
    
    reviews_per_user = int(request.data.get('reviews_per_user', 8))
    
    try:
        result = PeerReviewService.allocate_peer_reviews(round_id, reviews_per_user)
        return Response({
            'success': True,
            'message': '互评任务分配成功',
            'allocation': result
        }, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response({
            'success': False,
            'message': str(e.message) if hasattr(e, 'message') else str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'分配失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_peer_review_tasks(request):
    """
    获取当前用户的所有待完成互评任务
    GET /api/peer-reviews/tasks/
    """
    from .bidding_service import PeerReviewService
    from .serializers import PeerReviewAllocationSerializer
    
    user = request.user
    
    tasks = PeerReviewService.get_user_review_tasks(user)
    
    serializer = PeerReviewAllocationSerializer(tasks, many=True)
    
    return Response({
        'success': True,
        'task_count': tasks.count(),
        'tasks': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_peer_review(request, allocation_id):
    """
    提交互评打分
    POST /api/peer-reviews/allocations/{allocation_id}/submit/
    
    参数:
    - score: 评分（0-50）
    - comment: 评论（可选）
    """
    from .bidding_service import PeerReviewService
    from .serializers import PeerReviewSerializer
    
    user = request.user
    score = request.data.get('score')
    comment = request.data.get('comment', '')
    favorite = request.data.get('favorite', False)
    
    # 验证score
    if score is None:
        return Response({
            'success': False,
            'message': '评分不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        score = int(score)
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'message': '评分必须为整数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 验证分配任务属于当前用户
    from .models import PeerReviewAllocation
    allocation = get_object_or_404(PeerReviewAllocation, id=allocation_id, reviewer=user)
    
    try:
        review = PeerReviewService.submit_peer_review(allocation_id, score, comment, favorite)
        serializer = PeerReviewSerializer(review)
        return Response({
            'success': True,
            'message': '评分提交成功',
            'review': serializer.data
        }, status=status.HTTP_201_CREATED)
    except ValidationError as e:
        return Response({
            'success': False,
            'message': str(e.message) if hasattr(e, 'message') else str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'success': False,
            'message': f'提交失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chart_reviews(request, chart_id):
    """
    获取某个谱面的所有评分结果（匿名）
    GET /api/charts/{chart_id}/reviews/
    """
    from .models import Chart
    from .serializers import ChartDetailSerializer
    
    chart = get_object_or_404(Chart, id=chart_id)
    
    serializer = ChartDetailSerializer(chart, context={'request': request})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_extra_peer_review(request): # TODO 这里comment、comments参数命名混乱，需要重构。前端使用的是comments，model定义了comment。
    """
    提交额外的互评打分（用户自主选择的谱面）
    POST /api/peer-reviews/extra/
    
    参数:
    - chart_id: 谱面ID
    - score: 评分（0-最大分数）
    - comments: 评论（可选）
    - favorite: 真爱票，默认false
    """
    from .models import Chart, PeerReview, PeerReviewAllocation
    from .serializers import PeerReviewSerializer
    from django.conf import settings
    
    user = request.user
    chart_id = request.data.get('chart_id')
    score = request.data.get('score')
    comments = request.data.get('comments', '')
    favorite = request.data.get('favorite', False)
    
    # 验证参数
    if not chart_id:
        return Response({
            'success': False,
            'message': '谱面ID不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if score is None:
        return Response({
            'success': False,
            'message': '评分不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        score = int(score)
    except (ValueError, TypeError):
        return Response({
            'success': False,
            'message': '评分必须为整数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 获取最大分数配置
    max_score = getattr(settings, 'PEER_REVIEW_MAX_SCORE', 50)
    
    if score < 0 or score > max_score:
        return Response({
            'success': False,
            'message': f'评分必须在0到{max_score}之间'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 验证谱面存在
    chart = get_object_or_404(Chart, id=chart_id)
    
    # 检查是否是自己的谱面（不允许给自己的谱面评分）
    if chart.user == user or (chart.completion_bid_result and chart.completion_bid_result.user == user):
        return Response({
            'success': False,
            'message': '不能给自己参与制作的谱面评分'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 检查是否已经提交过额外评分（防止重复）
    existing_extra_review = PeerReview.objects.filter(
        reviewer=user,
        chart=chart,
        comment=comments,
        favorite=favorite,
        allocation__isnull=True  # 额外评分没有allocation
    ).first()
    
    if existing_extra_review:
        # 更新已有的额外评分
        existing_extra_review.score = score
        existing_extra_review.comment = comments
        existing_extra_review.favorite = favorite
        existing_extra_review.save()
        
        serializer = PeerReviewSerializer(existing_extra_review)
        return Response({
            'success': True,
            'message': '额外评分已更新',
            'review': serializer.data
        }, status=status.HTTP_200_OK)
    
    # 创建新的额外评分（不需要allocation）
    review = PeerReview.objects.create(
        chart=chart,
        reviewer=user,
        allocation=None,  # 额外评分没有allocation
        score=score,
        comment=comments,
        favorite=favorite
    )
    
    serializer = PeerReviewSerializer(review)
    return Response({
        'success': True,
        'message': '额外评分提交成功',
        'review': serializer.data
    }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': True,
        'chart': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_round_rankings(request, round_id):
    """
    获取某轮次的最终排名（基于平均分）
    GET /api/rankings/{round_id}/
    """
    from .models import Chart
    
    try:
        bidding_round = BiddingRound.objects.get(id=round_id)
    except BiddingRound.DoesNotExist:
        return Response({
            'success': False,
            'message': '竞标轮次不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 获取该轮所有已评分的谱面，按平均分排序
    charts = Chart.objects.filter(
        bidding_round=bidding_round,
        status__in=['reviewed']
    ).select_related('user', 'song').order_by('-average_score', '-total_score')
    
    rankings = []
    for idx, chart in enumerate(charts, 1):
        rankings.append({
            'rank': idx,
            'username': chart.user.username,
            'song_title': chart.song.title,
            'average_score': chart.average_score,
            'review_count': chart.review_count,
            'total_score': chart.total_score,
        })
    
    return Response({
        'success': True,
        'round': {
            'id': bidding_round.id,
            'name': bidding_round.name,
        },
        'total': len(rankings),
        'rankings': rankings
    }, status=status.HTTP_200_OK)

# ==================== 第二轮竞标API端点 ====================

# ==================== 第二轮竞标API端点（已废弃，使用统一的竞标系统） ====================
# 注意：以下代码已被注释，现在使用统一的BiddingRound和Bid系统来处理谱面竞标
# 创建 BiddingRound 并设置 bidding_type='chart' 来进行谱面竞标
