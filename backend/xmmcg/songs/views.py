from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Song, Bid, BiddingRound, BidResult, MAX_SONGS_PER_USER, MAX_BIDS_PER_USER, Banner, Announcement, CompetitionPhase
from .serializers import (
    SongUploadSerializer,
    SongDetailSerializer,
    SongListSerializer,
    SongUpdateSerializer,
    BannerSerializer,
    AnnouncementSerializer,
    CompetitionPhaseSerializer,
)
from .bidding_service import BiddingService


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
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_competition_phases(request):
    """获取所有比赛阶段信息"""
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
        
        serializer = SongListSerializer(songs_page, many=True)
        
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
    GET /api/bidding-rounds/ - 列出所有竞标轮次（从 CompetitionPhase 中提取）
    """
    # 从 CompetitionPhase 中获取竞标相关的阶段
    # phase_key 包含 'bidding' 的阶段
    phases = CompetitionPhase.objects.filter(
        phase_key__icontains='bidding',
        is_active=True
    ).order_by('start_time')
    
    now = timezone.now()
    data = []
    
    for phase in phases:
        # 根据时间判断状态
        if now < phase.start_time:
            status_val = 'pending'
        elif now > phase.end_time:
            status_val = 'completed'
        else:
            status_val = 'active'
        
        # 计算该阶段的竞标信息
        # 暂时返回0，后续可以通过关联 BiddingRound 来统计
        bid_count = 0
        
        data.append({
            'id': phase.id,
            'name': phase.name,
            'status': status_val,
            'status_display': '待开始' if status_val == 'pending' else ('进行中' if status_val == 'active' else '已完成'),
            'phase_key': phase.phase_key,
            'start_time': phase.start_time,
            'end_time': phase.end_time,
            'description': phase.description,
            'bid_count': bid_count,
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
        
        # 如果提供了 round_id，先尝试作为 CompetitionPhase ID
        # 然后查找或创建对应的 BiddingRound
        if round_id:
            try:
                # 尝试获取 CompetitionPhase
                phase = CompetitionPhase.objects.get(id=round_id, phase_key__icontains='bidding')
                
                # 查找或创建对应的 BiddingRound
                round_obj, created = BiddingRound.objects.get_or_create(
                    name=phase.name,
                    defaults={
                        'status': 'active' if timezone.now() < phase.end_time else 'completed'
                    }
                )
            except CompetitionPhase.DoesNotExist:
                # 如果不是 CompetitionPhase，尝试作为 BiddingRound ID
                try:
                    round_obj = BiddingRound.objects.get(id=round_id)
                except BiddingRound.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': '竞标轮次不存在'
                    }, status=status.HTTP_404_NOT_FOUND)
        else:
            # 获取当前活跃的竞标阶段
            now = timezone.now()
            active_phase = CompetitionPhase.objects.filter(
                phase_key__icontains='bidding',
                is_active=True,
                start_time__lte=now,
                end_time__gte=now
            ).first()
            
            if active_phase:
                # 查找或创建对应的 BiddingRound
                round_obj, created = BiddingRound.objects.get_or_create(
                    name=active_phase.name,
                    defaults={'status': 'active'}
                )
            else:
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
        
        bids_data = [{
            'id': bid.id,
            'song': SongListSerializer(bid.song).data,
            'amount': bid.amount,
            'is_dropped': bid.is_dropped,
            'created_at': bid.created_at,
        } for bid in bids]
        
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
    
    else:  # POST - 创建竞标
        song_id = request.data.get('song_id')
        amount = request.data.get('amount')
        round_id = request.data.get('round_id')
        
        if not song_id or not amount:
            return Response({
                'success': False,
                'message': '缺少必要字段：song_id, amount'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            song = Song.objects.get(id=song_id)
        except Song.DoesNotExist:
            return Response({
                'success': False,
                'message': '歌曲不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 获取竞标轮次（支持 CompetitionPhase ID 或 BiddingRound ID）
        if round_id:
            # 先尝试作为 CompetitionPhase ID
            try:
                phase = CompetitionPhase.objects.get(id=round_id, phase_key__icontains='bidding')
                # 查找或创建对应的 BiddingRound
                round_obj, created = BiddingRound.objects.get_or_create(
                    name=phase.name,
                    defaults={'status': 'active'}
                )
            except CompetitionPhase.DoesNotExist:
                # 尝试作为 BiddingRound ID
                try:
                    round_obj = BiddingRound.objects.get(id=round_id)
                except BiddingRound.DoesNotExist:
                    return Response({
                        'success': False,
                        'message': '竞标轮次不存在'
                    }, status=status.HTTP_404_NOT_FOUND)
        else:
            # 获取当前活跃的竞标阶段
            now = timezone.now()
            active_phase = CompetitionPhase.objects.filter(
                phase_key__icontains='bidding',
                is_active=True,
                start_time__lte=now,
                end_time__gte=now
            ).first()
            
            if active_phase:
                round_obj, created = BiddingRound.objects.get_or_create(
                    name=active_phase.name,
                    defaults={'status': 'active'}
                )
            else:
                return Response({
                    'success': False,
                    'message': '当前没有活跃的竞标轮次'
                }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            amount = int(amount)
            bid = BiddingService.create_bid(user, round_obj, song, amount)
            
            return Response({
                'success': True,
                'message': '竞标已创建',
                'bid': {
                    'id': bid.id,
                    'song': SongListSerializer(bid.song).data,
                    'amount': bid.amount,
                    'created_at': bid.created_at,
                }
            }, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response({
                'success': False,
                'message': str(e.message) if hasattr(e, 'message') else str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


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
        
        result = BiddingService.allocate_bids(round_obj.id)
        
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
    ).select_related('song').order_by('-bid_amount')
    
    results_data = [{
        'id': result.id,
        'song': SongListSerializer(result.song).data,
        'bid_amount': result.bid_amount,
        'allocation_type': result.allocation_type,
        'allocation_type_display': dict(BidResult.ALLOCATION_TYPE_CHOICES)[result.allocation_type],
        'allocated_at': result.allocated_at,
    } for result in results]
    
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_chart(request, result_id):
    """
    提交谱面
    POST /api/charts/{result_id}/submit/
    
    需要参数:
    - chart_url 或 chart_id_external (至少一个)
    
    用户通过竞标获得了歌曲后，可以提交谱面
    """
    from .models import BidResult, Chart
    from .serializers import ChartCreateSerializer, ChartSerializer
    
    user = request.user
    
    # 验证BidResult存在且属于当前用户
    bid_result = get_object_or_404(BidResult, id=result_id, user=user)
    
    # 检查是否已有谱面（允许覆盖）
    chart = Chart.objects.filter(
        user=user,
        song=bid_result.song,
        bidding_round=bid_result.bidding_round
    ).first()
    
    # 处理请求数据
    serializer = ChartCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if chart:
        # 更新现有谱面
        chart.chart_url = serializer.validated_data.get('chart_url', chart.chart_url)
        chart.chart_id_external = serializer.validated_data.get('chart_id_external', chart.chart_id_external)
        chart.status = 'submitted'
        chart.submitted_at = timezone.now()
        chart.save()
    else:
        # 创建新谱面
        chart = Chart.objects.create(
            bidding_round=bid_result.bidding_round,
            user=user,
            song=bid_result.song,
            bid_result=bid_result,
            status='submitted',
            chart_url=serializer.validated_data.get('chart_url'),
            chart_id_external=serializer.validated_data.get('chart_id_external'),
            submitted_at=timezone.now()
        )
    
    result_serializer = ChartSerializer(chart)
    return Response({
        'success': True,
        'message': '谱面提交成功',
        'chart': result_serializer.data
    }, status=status.HTTP_201_CREATED)


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
    
    serializer = ChartSerializer(charts, many=True)
    
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
def get_peer_review_tasks(request, round_id):
    """
    获取当前用户在某轮次需要完成的互评任务
    GET /api/peer-reviews/tasks/{round_id}/
    """
    from .bidding_service import PeerReviewService
    from .serializers import PeerReviewAllocationSerializer
    
    user = request.user
    
    try:
        bidding_round = BiddingRound.objects.get(id=round_id)
    except BiddingRound.DoesNotExist:
        return Response({
            'success': False,
            'message': '竞标轮次不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    tasks = PeerReviewService.get_user_review_tasks(user, bidding_round)
    
    serializer = PeerReviewAllocationSerializer(tasks, many=True)
    
    return Response({
        'success': True,
        'round': {
            'id': bidding_round.id,
            'name': bidding_round.name,
        },
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
        review = PeerReviewService.submit_peer_review(allocation_id, score, comment)
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
    
    serializer = ChartDetailSerializer(chart)
    
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

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def second_bidding_rounds(request):
    """
    第二轮竞标轮次管理
    GET /api/second-bidding-rounds/ - 列出所有第二轮竞标轮次
    POST /api/second-bidding-rounds/ - 创建新的第二轮竞标轮次（仅admin）
    """
    from .models import SecondBiddingRound, BiddingRound
    from .serializers import SecondBiddingRoundSerializer
    
    if request.method == 'GET':
        # 列出所有第二轮竞标轮次
        rounds = SecondBiddingRound.objects.all().select_related('bidding_round').order_by('-created_at')
        
        serializer = SecondBiddingRoundSerializer(rounds, many=True)
        
        return Response({
            'success': True,
            'total': rounds.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)
    
    elif request.method == 'POST':
        # 创建新的第二轮竞标轮次（仅admin）
        if not request.user.is_staff:
            return Response({
                'success': False,
                'message': '只有管理员可以创建竞标轮次'
            }, status=status.HTTP_403_FORBIDDEN)
        
        bidding_round_id = request.data.get('bidding_round_id')
        
        if not bidding_round_id:
            return Response({
                'success': False,
                'message': '必须指定第一轮竞标轮次ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            bidding_round = BiddingRound.objects.get(id=bidding_round_id)
        except BiddingRound.DoesNotExist:
            return Response({
                'success': False,
                'message': '指定的竞标轮次不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 检查是否已存在该轮次的第二轮竞标
        existing = SecondBiddingRound.objects.filter(first_bidding_round=bidding_round).exists()
        if existing:
            return Response({
                'success': False,
                'message': '该轮次已有对应的第二轮竞标'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建第二轮竞标轮次
        second_round = SecondBiddingRound.objects.create(
            first_bidding_round=bidding_round,
            name=f'{bidding_round.name} - Second Round',
            status='active'
        )
        
        serializer = SecondBiddingRoundSerializer(second_round)
        
        return Response({
            'success': True,
            'message': '第二轮竞标轮次创建成功',
            'second_bidding_round': serializer.data
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_charts_for_second_bidding(request, second_round_id):
    """
    获取可参与第二轮竞标的第一部分谱面列表
    GET /api/second-bidding-rounds/{round_id}/available-charts/
    """
    from .models import SecondBiddingRound
    from .serializers import AvailableChartSerializer
    from .bidding_service import SecondBiddingService
    
    try:
        second_round = SecondBiddingRound.objects.get(id=second_round_id)
    except SecondBiddingRound.DoesNotExist:
        return Response({
            'success': False,
            'message': '第二轮竞标轮次不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 获取可竞标的一半谱面
    available_charts = SecondBiddingService.get_available_part_one_charts(
        second_round, 
        user=request.user
    )
    
    # 分页处理
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    
    start = (page - 1) * page_size
    end = start + page_size
    
    total_count = available_charts.count()
    charts_page = available_charts[start:end]
    
    serializer = AvailableChartSerializer(charts_page, many=True)
    
    return Response({
        'success': True,
        'count': total_count,
        'page': page,
        'page_size': page_size,
        'total_pages': (total_count + page_size - 1) // page_size,
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_second_bid(request):
    """
    提交第二轮竞标
    POST /api/second-bids/
    
    请求体：
    {
        "second_bidding_round_id": 1,
        "target_chart_part_one_id": 5,
        "amount": 50
    }
    """
    from .models import SecondBiddingRound, Chart, SecondBid
    from .serializers import SecondBidSerializer
    
    second_round_id = request.data.get('second_bidding_round_id')
    chart_id = request.data.get('target_chart_part_one_id')
    amount = request.data.get('amount')
    
    if not all([second_round_id, chart_id, amount]):
        return Response({
            'success': False,
            'message': '缺少必要参数'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        second_round = SecondBiddingRound.objects.get(id=second_round_id)
    except SecondBiddingRound.DoesNotExist:
        return Response({
            'success': False,
            'message': '第二轮竞标轮次不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    try:
        target_chart = Chart.objects.get(id=chart_id)
    except Chart.DoesNotExist:
        return Response({
            'success': False,
            'message': '目标谱面不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if second_round.status != 'active':
        return Response({
            'success': False,
            'message': '该竞标轮次已关闭，无法提交竞标'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 验证竞标有效性
    is_valid, error_msg = SecondBiddingService.validate_second_bid(
        request.user, target_chart, amount
    )
    if not is_valid:
        return Response({
            'success': False,
            'message': error_msg
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 检查是否已对该谱面竞标过
    existing_bid = SecondBid.objects.filter(
        second_bidding_round=second_round,
        user=request.user,
        target_chart_part_one=target_chart
    ).first()
    
    if existing_bid and not existing_bid.is_dropped:
        return Response({
            'success': False,
            'message': '已对该谱面进行过竞标'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 创建竞标
    bid = SecondBid.objects.create(
        second_bidding_round=second_round,
        user=request.user,
        target_chart_part_one=target_chart,
        amount=int(amount)
    )
    
    serializer = SecondBidSerializer(bid)
    
    return Response({
        'success': True,
        'message': '竞标提交成功',
        'bid': serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_second_bids(request, second_round_id):
    """
    获取用户在某个第二轮竞标中的竞标记录
    GET /api/second-bidding-rounds/{round_id}/my-bids/
    """
    from .models import SecondBiddingRound, SecondBid
    from .serializers import SecondBidSerializer
    
    try:
        second_round = SecondBiddingRound.objects.get(id=second_round_id)
    except SecondBiddingRound.DoesNotExist:
        return Response({
            'success': False,
            'message': '第二轮竞标轮次不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 获取用户的竞标
    bids = SecondBid.objects.filter(
        second_bidding_round=second_round,
        user=request.user
    ).select_related('target_chart_part_one', 'target_chart_part_one__song').order_by('-created_at')
    
    serializer = SecondBidSerializer(bids, many=True)
    
    return Response({
        'success': True,
        'total': bids.count(),
        'bids': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def allocate_second_bids(request, second_round_id):
    """
    执行第二轮竞标分配（仅admin）
    POST /api/second-bidding-rounds/{round_id}/allocate/
    """
    from .models import SecondBiddingRound
    from .bidding_service import SecondBiddingService
    
    if not request.user.is_staff:
        return Response({
            'success': False,
            'message': '只有管理员可以执行分配'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        second_round = SecondBiddingRound.objects.get(id=second_round_id)
    except SecondBiddingRound.DoesNotExist:
        return Response({
            'success': False,
            'message': '第二轮竞标轮次不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if second_round.status != 'active':
        return Response({
            'success': False,
            'message': '只能对"进行中"的竞标轮次进行分配'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        result = SecondBiddingService.allocate_second_bids(second_round_id)
        
        second_round.status = 'completed'
        second_round.completed_at = timezone.now()
        second_round.save()
        
        return Response({
            'success': True,
            'message': '分配完成',
            'allocation_result': result
        }, status=status.HTTP_200_OK)
    
    except ValidationError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_second_bid_results(request, second_round_id):
    """
    获取用户的第二轮竞标分配结果
    GET /api/second-bidding-rounds/{round_id}/my-results/
    """
    from .models import SecondBiddingRound
    from .serializers import SecondBidResultSerializer
    from .bidding_service import SecondBiddingService
    
    try:
        second_round = SecondBiddingRound.objects.get(id=second_round_id)
    except SecondBiddingRound.DoesNotExist:
        return Response({
            'success': False,
            'message': '第二轮竞标轮次不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # 获取用户的分配结果
    results = SecondBiddingService.get_second_bid_results(request.user, second_round)
    
    serializer = SecondBidResultSerializer(results, many=True)
    
    return Response({
        'success': True,
        'total': results.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)