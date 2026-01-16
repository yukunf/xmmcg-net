from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

from .models import Song, Bid, BiddingRound, BidResult, MAX_SONGS_PER_USER, MAX_BIDS_PER_USER
from .serializers import (
    SongUploadSerializer,
    SongDetailSerializer,
    SongListSerializer,
    SongUpdateSerializer,
)
from .bidding_service import BiddingService


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

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def bidding_rounds_root(request):
    """
    竞标轮次管理
    GET /api/bidding-rounds/ - 列出所有竞标轮次
    POST /api/bidding-rounds/ - 创建新的竞标轮次（需要 admin 权限）
    """
    if request.method == 'GET':
        # 列出所有竞标轮次
        rounds = BiddingRound.objects.all().order_by('-created_at')
        
        data = []
        for round_obj in rounds:
            bid_count = Bid.objects.filter(bidding_round=round_obj).count()
            result_count = BidResult.objects.filter(bidding_round=round_obj).count()
            
            data.append({
                'id': round_obj.id,
                'name': round_obj.name,
                'status': round_obj.status,
                'status_display': round_obj.get_status_display(),
                'created_at': round_obj.created_at,
                'started_at': round_obj.started_at,
                'completed_at': round_obj.completed_at,
                'bid_count': bid_count,
                'result_count': result_count,
            })
        
        return Response({
            'success': True,
            'count': len(data),
            'rounds': data
        }, status=status.HTTP_200_OK)
    
    else:  # POST - 创建竞标轮次
        # 仅 admin 用户可以创建
        if not request.user.is_authenticated or not request.user.is_staff:
            return Response({
                'success': False,
                'message': '需要管理员权限'
            }, status=status.HTTP_403_FORBIDDEN)
        
        name = request.data.get('name', '')
        if not name:
            return Response({
                'success': False,
                'message': '竞标轮次名称不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        round_obj = BiddingRound.objects.create(
            name=name,
            status='active'
        )
        
        return Response({
            'success': True,
            'message': '竞标轮次已创建',
            'round': {
                'id': round_obj.id,
                'name': round_obj.name,
                'status': round_obj.status,
                'created_at': round_obj.created_at,
            }
        }, status=status.HTTP_201_CREATED)


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
        
        if round_id:
            try:
                round_obj = BiddingRound.objects.get(id=round_id, status='active')
            except BiddingRound.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '竞标轮次不存在或已结束'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # 获取最新的活跃竞标轮次
            round_obj = BiddingRound.objects.filter(status='active').first()
            if not round_obj:
                return Response({
                    'success': True,
                    'message': '当前没有活跃的竞标轮次',
                    'bids': []
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
        
        # 获取竞标轮次
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

