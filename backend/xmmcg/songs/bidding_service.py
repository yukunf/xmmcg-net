"""
竞标管理服务
处理竞标的创建、验证、分配等业务逻辑
"""

import random
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import Bid, BidResult, BiddingRound, Song, MAX_SONGS_PER_USER
from users.models import UserProfile


class BiddingService:
    """竞标服务类"""
    
    @staticmethod
    @transaction.atomic
    def allocate_bids(bidding_round_id):
        """
        执行竞标分配逻辑
        
        算法：
        1. 获取该轮次的所有有效竞标（未drop）
        2. 按出价从高到低排序
        3. 逐个处理竞标：
           - 如果该歌曲还未被分配，将该竞标标记为中标
           - 该歌曲的其他竞标标记为drop
        4. 对于未获得任何歌曲的用户，从未被分配的歌曲中随机分配
        5. 标记该轮次为已完成
        
        Args:
            bidding_round_id: 竞标轮次ID
            
        Returns:
            dict: 包含分配结果统计信息
            
        Raises:
            ValidationError: 如果竞标轮次不存在或状态不适合分配
        """
        
        # 获取竞标轮次
        try:
            bidding_round = BiddingRound.objects.get(id=bidding_round_id)
        except BiddingRound.DoesNotExist:
            raise ValidationError('竞标轮次不存在')
        
        if bidding_round.status != 'active':
            raise ValidationError(f'只能对"进行中"的竞标轮次进行分配')
        
        # 清空之前的分配结果（如果有重新分配）
        BidResult.objects.filter(bidding_round=bidding_round).delete()
        
        # 获取所有有效竞标，按出价从高到低、时间从早到晚（同价格按先来先得）
        all_bids = Bid.objects.filter(
            bidding_round=bidding_round,
            is_dropped=False
        ).select_related('user', 'song').order_by('-amount', 'created_at')
        
        # 追踪已分配的歌曲和用户
        allocated_songs = set()  # 已分配的歌曲ID集合
        allocated_users = {}     # 用户ID -> [歌曲列表]，用于追踪每个用户获得的歌曲
        
        # 第一阶段：按出价从高到低进行分配
        for bid in all_bids:
            if bid.song.id not in allocated_songs:
                # 该歌曲尚未被分配，分配给该竞标者
                BidResult.objects.create(
                    bidding_round=bidding_round,
                    user=bid.user,
                    song=bid.song,
                    bid_amount=bid.amount,
                    allocation_type='win'
                )
                allocated_songs.add(bid.song.id)
                
                if bid.user.id not in allocated_users:
                    allocated_users[bid.user.id] = []
                allocated_users[bid.user.id].append(bid.song.id)
            else:
                # 该歌曲已被更高出价者获得，标记此竞标为drop
                bid.is_dropped = True
                bid.save()
        
        # 获取所有歌曲
        all_songs = Song.objects.all()
        all_song_ids = set(song.id for song in all_songs)
        
        # 获取未被分配的歌曲
        unallocated_songs = list(all_song_ids - allocated_songs)
        
        # 第二阶段：对于未获得任何歌曲的用户，随机分配
        # 获取参与竞标的所有用户
        bidding_users = set(bid.user.id for bid in all_bids)
        
        for user_id in bidding_users:
            # 检查该用户是否已经获得了歌曲
            if user_id not in allocated_users:
                # 用户未获得任何歌曲，随机分配一个
                if unallocated_songs:
                    random_song_id = random.choice(unallocated_songs)
                    from django.contrib.auth.models import User
                    user = User.objects.get(id=user_id)
                    
                    BidResult.objects.create(
                        bidding_round=bidding_round,
                        user=user,
                        song_id=random_song_id,
                        bid_amount=0,  # 随机分配没有出价金额
                        allocation_type='random'
                    )
                    allocated_songs.add(random_song_id)
                    unallocated_songs.remove(random_song_id)
        
        # 标记竞标轮次为已完成
        bidding_round.status = 'completed'
        bidding_round.save()
        
        # 返回统计信息
        return {
            'status': 'success',
            'message': '竞标分配完成',
            'total_songs': len(all_song_ids),
            'allocated_songs': len(allocated_songs),
            'unallocated_songs': len(unallocated_songs),
            'winners': len(allocated_users),
            'total_bidders': len(bidding_users),
        }
    
    @staticmethod
    def create_bid(user, bidding_round, song, amount):
        """
        创建竞标
        
        Args:
            user: 竞标用户
            bidding_round: 竞标轮次
            song: 目标歌曲
            amount: 竞标金额
            
        Returns:
            Bid: 创建的竞标对象
            
        Raises:
            ValidationError: 如果竞标不合法
        """
        
        # 验证竞标轮次状态
        if bidding_round.status != 'active':
            raise ValidationError('只能在竞标进行中时创建新竞标')
        
        # 验证用户代币余额
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.token < amount:
                raise ValidationError('代币余额不足')
        except UserProfile.DoesNotExist:
            raise ValidationError('用户资料不存在')
        
        # 验证竞标金额
        if amount <= 0:
            raise ValidationError('竞标金额必须大于0')
        
        # 验证用户在该轮次的竞标数量
        bid_count = Bid.objects.filter(
            bidding_round=bidding_round,
            user=user,
            is_dropped=False
        ).count()
        
        from .models import MAX_BIDS_PER_USER
        if bid_count >= MAX_BIDS_PER_USER:
            raise ValidationError(
                f'超过每轮最多竞标 {MAX_BIDS_PER_USER} 个歌曲的限制'
            )
        
        # 检查用户是否已经对该歌曲竞标过
        existing_bid = Bid.objects.filter(
            bidding_round=bidding_round,
            user=user,
            song=song,
            is_dropped=False
        ).first()
        
        if existing_bid:
            raise ValidationError('您已经对该歌曲竞标过了')
        
        # 创建竞标
        bid = Bid.objects.create(
            bidding_round=bidding_round,
            user=user,
            song=song,
            amount=amount
        )
        
        return bid
    
    @staticmethod
    def get_user_bids(user, bidding_round):
        """
        获取用户在指定竞标轮次的所有竞标
        
        Args:
            user: 用户对象
            bidding_round: 竞标轮次
            
        Returns:
            QuerySet: 用户的竞标集合
        """
        return Bid.objects.filter(
            bidding_round=bidding_round,
            user=user
        ).select_related('song').order_by('-amount')
    
    @staticmethod
    def get_user_results(user, bidding_round):
        """
        获取用户在指定竞标轮次的分配结果
        
        Args:
            user: 用户对象
            bidding_round: 竞标轮次
            
        Returns:
            QuerySet: 用户的分配结果集合
        """
        return BidResult.objects.filter(
            bidding_round=bidding_round,
            user=user
        ).select_related('song').order_by('-bid_amount')
