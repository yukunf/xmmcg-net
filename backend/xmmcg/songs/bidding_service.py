"""
竞标管理服务
处理竞标的创建、验证、分配等业务逻辑
支持歌曲竞标和谱面竞标的统一处理
"""

import random
from django.db import transaction
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Bid, BidResult, BiddingRound, Song, Chart, MAX_SONGS_PER_USER, RANDOM_ALLOCATION_COST
from users.models import UserProfile


class BiddingService:
    """竞标服务类"""
    
    @staticmethod
    @transaction.atomic
    def allocate_bids(bidding_round_id, priority_self=False):
        """
        执行竞标分配逻辑（统一支持歌曲和谱面竞标）
        
        算法：
        1. 根据BiddingRound.bidding_type确定竞标类型（song/chart）
        2. 获取该轮次的所有有效竞标（未drop）
        3. 按出价从高到低排序
        4. 逐个处理竞标：
           - 如果该目标（歌曲或谱面）还未被分配，将该竞标标记为中标
           - 该目标的其他竞标标记为drop
        5. 对于未获得任何目标的用户，从未被分配的目标中随机分配
           - 如果priority_self=True且为谱面竞标，优先分配用户自己的半成品谱面
        6. 标记该轮次为已完成
        
        Args:
            bidding_round_id: 竞标轮次ID
            priority_self: 是否优先分配自己的半成品谱面（仅谱面竞标有效，默认False）
            
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
        
        bidding_type = bidding_round.bidding_type  # 'song' or 'chart'
        
        # 清空之前的分配结果（如果有重新分配）
        BidResult.objects.filter(bidding_round=bidding_round).delete()
        
        # 获取所有有效竞标（根据类型选择正确的关联）
        if bidding_type == 'song':
            all_bids = list(Bid.objects.filter(
                bidding_round=bidding_round,
                is_dropped=False,
                bid_type='song'
            ).select_related('user', 'song'))
        else:  # chart
            all_bids = list(Bid.objects.filter(
                bidding_round=bidding_round,
                is_dropped=False,
                bid_type='chart'
            ).select_related('user', 'chart', 'chart__user'))
        
        # 按出价从高到低排序，同价格随机打乱
        from collections import defaultdict
        bids_by_amount = defaultdict(list)
        for bid in all_bids:
            bids_by_amount[bid.amount].append(bid)
        
        # 对每个价格组内随机打乱
        sorted_bids = []
        for amount in sorted(bids_by_amount.keys(), reverse=True):
            group = bids_by_amount[amount]
            random.shuffle(group)  # 同价格随机排序
            sorted_bids.extend(group)
        
        all_bids = sorted_bids
        
        # 追踪已分配的目标和用户
        allocated_targets = set()  # 已分配的目标ID集合（歌曲或谱面）
        allocated_users = {}       # 用户ID -> 目标ID（每个用户最多一个）
        
        # 第一阶段：按出价从高到低进行分配
        for bid in all_bids:
            # 如果用户已经中标，skip该用户的所有后续竞标
            if bid.user.id in allocated_users:
                # 用户已经中标，drop这个竞标
                bid.is_dropped = True
                bid.save()
                continue
            
            target_id = bid.song.id if bidding_type == 'song' else bid.chart.id
            
            if target_id not in allocated_targets:
                # 该目标尚未被分配，分配给该竞标者
                if bidding_type == 'song':
                    BidResult.objects.create(
                        bidding_round=bidding_round,
                        user=bid.user,
                        bid_type='song',
                        song=bid.song,
                        bid_amount=bid.amount,
                        allocation_type='win'
                    )
                else:  # chart
                    BidResult.objects.create(
                        bidding_round=bidding_round,
                        user=bid.user,
                        bid_type='chart',
                        chart=bid.chart,
                        bid_amount=bid.amount,
                        allocation_type='win'
                    )
                
                allocated_targets.add(target_id)
                allocated_users[bid.user.id] = target_id  # 记录用户已中标
                
                # 立即drop该用户的所有其他竞标
                Bid.objects.filter(
                    bidding_round=bidding_round,
                    user=bid.user,
                    is_dropped=False
                ).exclude(id=bid.id).update(is_dropped=True)
            else:
                # 该目标已被更高出价者获得，标记此竞标为drop
                bid.is_dropped = True
                bid.save()
        
        # 获取所有可分配的目标
        if bidding_type == 'song':
            all_targets = Song.objects.all()
            all_target_ids = set(song.id for song in all_targets)
        else:  # chart
            # 谱面竞标：只能竞标第一部分且没有完成第二部分的谱面
            all_targets = Chart.objects.filter(
                is_part_one=True,
                status__in=['submitted', 'reviewed', 'part_submitted']
            )
            # 排除已有第二部分的谱面
            from django.db.models import OuterRef, Exists
            part_two_exists = Chart.objects.filter(
                part_one_chart=OuterRef('pk'),
                is_part_one=False
            )
            all_targets = all_targets.exclude(Exists(part_two_exists))
            all_target_ids = set(chart.id for chart in all_targets)
        
        # 获取未被分配的目标
        unallocated_targets = list(all_target_ids - allocated_targets)
        
        # 对于谱面竞标，预先建立chart_id到user_id的映射（优化查询）
        chart_owner_map = {}
        if bidding_type == 'chart' and priority_self:
            charts_info = Chart.objects.filter(id__in=unallocated_targets).values('id', 'user_id')
            chart_owner_map = {chart['id']: chart['user_id'] for chart in charts_info}
        
        # 第二阶段：对于未获得任何目标的用户，随机分配（需扣除保底代币）
        # 获取参与竞标的所有用户
        bidding_users = set(bid.user.id for bid in all_bids)
        
        for user_id in bidding_users:
            # 检查该用户是否已经获得了目标
            if user_id not in allocated_users:
                user = User.objects.get(id=user_id)
                target_id = None
                
                # 如果启用priority_self且是谱面竞标，优先分配自己的半成品谱面
                if priority_self and bidding_type == 'chart' and unallocated_targets:
                    # 查找该用户自己的未分配的半成品谱面
                    user_own_charts = [
                        chart_id for chart_id in unallocated_targets 
                        if chart_owner_map.get(chart_id) == user_id
                    ]
                    if user_own_charts:
                        target_id = random.choice(user_own_charts)
                
                # 如果没有找到自己的谱面（或不启用priority_self），随机分配
                if target_id is None and unallocated_targets:
                    target_id = random.choice(unallocated_targets)
                
                # 创建分配结果
                if target_id is not None:
                    if bidding_type == 'song':
                        BidResult.objects.create(
                            bidding_round=bidding_round,
                            user=user,
                            bid_type='song',
                            song_id=target_id,
                            bid_amount=RANDOM_ALLOCATION_COST,  # 保底分配需要支付代币
                            allocation_type='random'
                        )
                    else:  # chart
                        BidResult.objects.create(
                            bidding_round=bidding_round,
                            user=user,
                            bid_type='chart',
                            chart_id=target_id,
                            bid_amount=RANDOM_ALLOCATION_COST,
                            allocation_type='random'
                        )
                    
                    allocated_targets.add(target_id)
                    unallocated_targets.remove(target_id)
        
        # 标记竞标轮次为已完成
        bidding_round.status = 'completed'
        bidding_round.completed_at = timezone.now()
        bidding_round.save()
        
        # 处理代币扣除
        token_deduction = BiddingService.process_allocation_tokens(bidding_round.id)
        
        # 返回统计信息
        target_type_name = '歌曲' if bidding_type == 'song' else '谱面'
        return {
            'status': 'success',
            'message': f'{target_type_name}竞标分配完成',
            'bidding_type': bidding_type,
            'total_targets': len(all_target_ids),
            'allocated_targets': len(allocated_targets),
            'unallocated_targets': len(unallocated_targets),
            'winners': len(allocated_users),
            'total_bidders': len(bidding_users),
            'token_deduction': token_deduction,
        }
    
    @staticmethod
    def create_bid(user, bidding_round, amount, song=None, chart=None):
        """
        创建竞标（支持歌曲或谱面）
        
        Args:
            user: 竞标用户
            bidding_round: 竞标轮次
            amount: 竞标金额
            song: 目标歌曲（歌曲竞标时使用）
            chart: 目标谱面（谱面竞标时使用）
            
        Returns:
            Bid: 创建的竞标对象
            
        Raises:
            ValidationError: 如果竞标不合法
        """
        
        # 验证竞标轮次状态
        if bidding_round.status != 'active':
            raise ValidationError('只能在竞标进行中时创建新竞标')
        
        # 验证bid_type与目标一致
        if song and chart:
            raise ValidationError('不能同时竞标歌曲和谱面')
        if not song and not chart:
            raise ValidationError('必须指定竞标目标（歌曲或谱面）')
        
        bid_type = 'song' if song else 'chart'
        
        # 验证竞标类型与轮次类型一致
        if bidding_round.bidding_type != bid_type:
            raise ValidationError(f'该轮次是{bidding_round.get_bidding_type_display()}，不能竞标{"歌曲" if bid_type == "chart" else "谱面"}')
        
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
        
        # # 对于谱面竞标，验证不能竞标自己的谱面  修改：我们现在允许竞标自己的
        # if chart and chart.user == user:
        #     raise ValidationError('不能竞标自己的谱面')
        
        # 对于谱面竞标，验证谱面状态必须是 part_submitted（半成品）
        if chart and chart.status != 'part_submitted':
            raise ValidationError(f'只能竞标半成品谱面，该谱面当前状态为：{chart.get_status_display()}')
        
        # 验证用户在该轮次的竞标数量
        bid_count = Bid.objects.filter(
            bidding_round=bidding_round,
            user=user,
            is_dropped=False
        ).count()
        
        from .models import MAX_BIDS_PER_USER
        if bid_count >= MAX_BIDS_PER_USER:
            raise ValidationError(
                f'超过每轮最多竞标 {MAX_BIDS_PER_USER} 个的限制'
            )
        
        # 检查用户是否已经对该目标竞标过
        if song:
            existing_bid = Bid.objects.filter(
                bidding_round=bidding_round,
                user=user,
                song=song,
                is_dropped=False
            ).first()
            if existing_bid:
                raise ValidationError('您已经对该歌曲竞标过了')
        else:  # chart
            existing_bid = Bid.objects.filter(
                bidding_round=bidding_round,
                user=user,
                chart=chart,
                is_dropped=False
            ).first()
            if existing_bid:
                raise ValidationError('您已经对该谱面竞标过了')
        
        # 创建竞标
        bid = Bid.objects.create(
            bidding_round=bidding_round,
            user=user,
            bid_type=bid_type,
            song=song,
            chart=chart,
            amount=amount
        )
        
        return bid
    
    @staticmethod
    @transaction.atomic
    def process_allocation_tokens(bidding_round_id):
        """
        处理竞标分配后的代币扣除
        
        逻辑：
        1. 获取该轮次的所有分配结果
        2. 对于每个中标的用户，从其代币中扣除竞标金额
        3. 随机分配的用户（bid_amount=0）不扣除代币
        4. 返回处理统计
        
        Args:
            bidding_round_id: 竞标轮次ID
            
        Returns:
            dict: 包含代币处理统计信息
            
        Raises:
            ValidationError: 如果处理失败
        """
        
        # 获取竞标轮次
        try:
            bidding_round = BiddingRound.objects.get(id=bidding_round_id)
        except BiddingRound.DoesNotExist:
            raise ValidationError('竞标轮次不存在')
        
        # 获取该轮次的所有分配结果（包括竞价和随机分配）
        results = BidResult.objects.filter(
            bidding_round=bidding_round
        ).select_related('user', 'song')
        
        total_deducted = 0
        users_deducted = 0
        failed_users = []
        
        for result in results:
            try:
                # 获取或创建用户资料
                profile, created = UserProfile.objects.get_or_create(user=result.user)
                
                # 验证代币足够
                if profile.token < result.bid_amount:
                    failed_users.append({
                        'user': result.user.username,
                        'required': result.bid_amount,
                        'available': profile.token
                    })
                    continue
                
                # 扣除代币
                profile.token -= result.bid_amount
                profile.save()
                
                total_deducted += result.bid_amount
                users_deducted += 1
                
            except Exception as e:
                failed_users.append({
                    'user': result.user.username,
                    'error': str(e)
                })
        
        return {
            'total_deducted': total_deducted,
            'users_deducted': users_deducted,
            'failed_users': failed_users,
            'failed_count': len(failed_users),
        }
    
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


class PeerReviewService:
    """互评服务类 - 处理谱面评分相关逻辑"""
    
    @staticmethod
    @transaction.atomic
    def allocate_peer_reviews(bidding_round_id, reviews_per_user=8):
        """
        为某个竞标轮次分配互评任务
        
        核心需求：
        1. 每个提交谱面的用户要收到exactly 8个评分
        2. 每个评分者要评分exactly 8个谱面
        3. 用户不能评自己的谱面
        
        算法（平衡二分图匹配）：
        - 使用贪心算法进行逐步分配
        - 维护每个评分者和谱面的剩余评分数
        - 采用轮转策略保证均衡
        
        Args:
            bidding_round_id: 竞标轮次ID
            reviews_per_user: 每个用户的评分任务数（默认8）
            
        Returns:
            dict: 包含分配结果统计
            
        Raises:
            ValidationError: 如果条件不足以进行平衡分配
        """
        from .models import Chart, PeerReviewAllocation
        
        # 获取竞标轮次
        try:
            bidding_round = BiddingRound.objects.get(id=bidding_round_id)
        except BiddingRound.DoesNotExist:
            raise ValidationError('竞标轮次不存在')
        
        # 获取该轮所有已提交的谱面
        charts = Chart.objects.filter(
            bidding_round=bidding_round,
            status__in=['submitted', 'under_review', 'reviewed']
        ).select_related('user', 'song')
        
        if not charts.exists():
            raise ValidationError('该轮次还没有提交的谱面')
        
        # 获取参与评分的用户（即提交了谱面的用户）
        reviewers = User.objects.filter(
            id__in=charts.values_list('user_id', flat=True)
        ).distinct()
        
        num_charts = charts.count()
        num_reviewers = reviewers.count()
        
        # 验证能否进行平衡分配
        # 理想情况：num_charts * reviews_per_user = num_reviewers * reviews_per_user
        total_assignments_needed = num_charts * reviews_per_user
        total_capacity = num_reviewers * reviews_per_user
        
        if total_assignments_needed != total_capacity:
            raise ValidationError(
                f'无法进行平衡分配：'
                f'{num_charts}个谱面 × {reviews_per_user}个评分 = {total_assignments_needed}，'
                f'但{num_reviewers}个评分者 × {reviews_per_user}个任务 = {total_capacity}'
            )
        
        # 清空已有的分配（重新分配）
        PeerReviewAllocation.objects.filter(
            bidding_round=bidding_round
        ).delete()
        
        # 转换为列表便于操作
        charts_list = list(charts)
        reviewers_list = list(reviewers)
        
        # 初始化分配计数
        chart_review_counts = {chart.id: 0 for chart in charts_list}
        reviewer_task_counts = {reviewer.id: 0 for reviewer in reviewers_list}
        
        # 创建分配记录
        allocations = []
        
        # 使用循环轮转算法进行分配
        reviewer_idx = 0
        for _ in range(total_assignments_needed):
            # 找到需要被评分的谱面（评分数最少的）
            chart = min(charts_list, key=lambda c: chart_review_counts[c.id])
            chart_owner_id = chart.user_id
            
            # 循环找到一个合适的评分者
            found_reviewer = False
            attempts = 0
            while attempts < len(reviewers_list):
                reviewer = reviewers_list[reviewer_idx % len(reviewers_list)]
                reviewer_idx += 1
                attempts += 1
                
                # 检查这个评分者是否满足条件
                # 1. 没有超过任务数限制
                # 2. 不是该谱面的所有者
                # 3. 还没有评过这个谱面
                if (reviewer_task_counts[reviewer.id] < reviews_per_user and
                    reviewer.id != chart_owner_id):
                    
                    # 检查是否已分配过
                    existing = PeerReviewAllocation.objects.filter(
                        bidding_round=bidding_round,
                        reviewer=reviewer,
                        chart=chart
                    ).exists()
                    
                    if not existing:
                        # 创建分配
                        allocation = PeerReviewAllocation(
                            bidding_round=bidding_round,
                            reviewer=reviewer,
                            chart=chart
                        )
                        allocations.append(allocation)
                        
                        chart_review_counts[chart.id] += 1
                        reviewer_task_counts[reviewer.id] += 1
                        found_reviewer = True
                        break
            
            if not found_reviewer:
                raise ValidationError(
                    f'分配失败：无法为谱面 {chart.id} 找到合适的评分者'
                )
        
        # 批量创建分配记录
        PeerReviewAllocation.objects.bulk_create(allocations)
        
        # 更新所有谱面状态为 under_review
        Chart.objects.filter(
            bidding_round=bidding_round,
            status__in=['submitted']
        ).update(status='under_review')
        
        return {
            'bidding_round_id': bidding_round_id,
            'total_allocations': len(allocations),
            'charts_count': num_charts,
            'reviewers_count': num_reviewers,
            'reviews_per_chart': reviews_per_user,
            'tasks_per_reviewer': reviews_per_user,
            'status': 'success'
        }
    
    @staticmethod
    def submit_peer_review(allocation_id, score, comment=None):
        """
        提交互评打分
        
        Args:
            allocation_id: 分配任务ID
            score: 评分（0-PEER_REVIEW_MAX_SCORE）
            comment: 评论（可选）
            
        Returns:
            PeerReview: 创建的评分记录
            
        Raises:
            ValidationError: 如果分配不存在或已评分
        """
        from .models import PeerReviewAllocation, PeerReview, PEER_REVIEW_MAX_SCORE
        
        try:
            allocation = PeerReviewAllocation.objects.get(id=allocation_id)
        except PeerReviewAllocation.DoesNotExist:
            raise ValidationError('分配任务不存在')
        
        if allocation.status == 'completed':
            raise ValidationError('该任务已完成')
        
        # 验证评分
        if score < 0 or score > PEER_REVIEW_MAX_SCORE:
            raise ValidationError(f'评分必须在0-{PEER_REVIEW_MAX_SCORE}之间')
        
        # 创建评分记录
        review = PeerReview.objects.create(
            allocation=allocation,
            bidding_round=allocation.bidding_round,
            reviewer=allocation.reviewer,
            chart=allocation.chart,
            score=score,
            comment=comment
        )
        
        # 标记分配为已完成
        allocation.status = 'completed'
        allocation.save()
        
        # 更新谱面的评分统计
        chart = allocation.chart
        chart.review_count += 1
        chart.total_score += score
        chart.calculate_average_score()
        
        # 检查该谱面是否已收到所有评分
        if chart.review_count >= 8:  # PEER_REVIEW_TASKS_PER_USER
            chart.status = 'reviewed'
            chart.review_completed_at = review.created_at
            chart.save()
        else:
            chart.save()
        
        return review
    
    @staticmethod
    def get_user_review_tasks(user, bidding_round):
        """
        获取用户在某轮次要完成的评分任务
        
        Args:
            user: 用户对象
            bidding_round: 竞标轮次
            
        Returns:
            QuerySet: 用户的待评分任务
        """
        from .models import PeerReviewAllocation
        
        return PeerReviewAllocation.objects.filter(
            bidding_round=bidding_round,
            reviewer=user,
            status='pending'
        ).select_related('chart', 'chart__user', 'chart__song')
    
    @staticmethod
    def get_chart_reviews(chart):
        """
        获取某个谱面收到的所有评分（匿名）
        
        Args:
            chart: Chart对象
            
        Returns:
            QuerySet: 评分记录集合（不包含评分者信息）
        """
        from .models import PeerReview
        
        return PeerReview.objects.filter(
            chart=chart
        ).values('score', 'comment', 'created_at').order_by('-created_at')

# ==================== 第二轮竞标服务 ====================

# ==================== 第二轮竞标服务（已废弃，使用统一的BiddingService） ====================
# 注意：以下代码已被注释，现在使用统一的BiddingService来处理歌曲和谱面竞标
# 请创建 BiddingRound 并设置 bidding_type='chart' 来进行谱面竞标

# class SecondBiddingService:
#     """第二轮竞标服务类 - 处理谱面竞标逻辑"""
#     
#     @staticmethod
#     @transaction.atomic
#     def allocate_second_bids(second_bidding_round_id):
#         """
#         执行第二轮竞标分配逻辑（用户竞标其他人的一半谱面）
#         
#         算法：
#         1. 获取该第二轮竞标的所有有效竞标（未drop）
#         2. 按出价从高到低排序
#         3. 逐个处理竞标：
#            - 如果该一半谱面还未被分配，将该竞标标记为中标
#            - 该一半谱面的其他竞标标记为drop
#         4. 对于未获得任何谱面的用户，从未被分配的谱面中随机分配
#         5. 为每个中标者创建Chart对象（第二部分）
#         6. 标记该轮次为已完成
#         
#         Args:
#             second_bidding_round_id: 第二轮竞标轮次ID
#             
#         Returns:
#             dict: 包含分配结果统计信息
#             
#         Raises:
#             ValidationError: 如果轮次不存在或状态不适合分配
#         """
#         pass
#     
#     @staticmethod
#     def validate_second_bid(user, target_chart_part_one, amount):
#         """验证第二轮竞标是否有效"""
#         pass
#     
#     @staticmethod
#     def get_available_part_one_charts(second_bidding_round, user=None):
#         """获取可参与第二轮竞标的第一部分谱面列表"""
#         pass
#     
#     @staticmethod
#     def get_second_bid_results(user, second_bidding_round):
#         """获取用户在某个第二轮竞标中的分配结果"""
#         pass
    """第二轮竞标服务类"""
    
    @staticmethod
    @transaction.atomic
    def allocate_second_bids(second_bidding_round_id):
        """
        执行第二轮竞标分配逻辑
        
        第二轮竞标针对第一轮中已经完成第一半谱面的歌曲
        选手用剩余的token竞标以获得他人的一半谱面，然后完成后半部分
        
        算法：
        1. 获取该轮次的所有有效竞标（未drop）
        2. 按出价从高到低排序
        3. 逐个处理竞标：
           - 如果该一半谱面还未被分配，将该竞标标记为中标
           - 该一半谱面的其他竞标标记为drop
        4. 对于未获得任何谱面的用户，从未被分配的谱面中随机分配
        5. 为每个中标者创建Chart对象（第二部分）
        6. 标记该轮次为已完成
        
        Args:
            second_bidding_round_id: 第二轮竞标轮次ID
            
        Returns:
            dict: 包含分配结果统计信息
            
        Raises:
            ValidationError: 如果轮次不存在或状态不适合分配
        """
        from .models import SecondBiddingRound, SecondBid, SecondBidResult, Chart
        
        # 获取第二轮竞标轮次
        try:
            second_bidding_round = SecondBiddingRound.objects.get(id=second_bidding_round_id)
        except SecondBiddingRound.DoesNotExist:
            raise ValidationError('第二轮竞标轮次不存在')
        
        if second_bidding_round.status != 'active':
            raise ValidationError('只能对"进行中"的竞标轮次进行分配')
        
        # 清空之前的分配结果
        SecondBidResult.objects.filter(second_bidding_round=second_bidding_round).delete()
        
        # 获取所有有效的第二轮竞标
        all_bids = SecondBid.objects.filter(
            second_bidding_round=second_bidding_round,
            is_dropped=False
        ).select_related('bidder', 'target_chart_part_one').order_by('-amount', 'created_at')
        
        # 追踪已分配的一半谱面和用户
        allocated_charts = set()  # 已分配的一半谱面ID集合
        allocated_users = {}       # 用户ID -> [一半谱面列表]
        
        # 第一阶段：按出价从高到低进行分配
        for bid in all_bids:
            chart_id = bid.target_chart_part_one.id
            if chart_id not in allocated_charts:
                # 该一半谱面尚未被分配，分配给该竞标者
                bid_result = SecondBidResult.objects.create(
                    second_bidding_round=second_bidding_round,
                    winner=bid.bidder,
                    part_one_chart=bid.target_chart_part_one,
                    bid_amount=bid.amount,
                    allocation_type='win'
                )
                
                # 创建第二部分谱面
                part_two_chart = Chart.objects.create(
                    bidding_round=second_bidding_round.first_bidding_round,
                    user=bid.bidder,
                    song=bid.target_chart_part_one.song,
                    is_part_one=False,
                    part_one_chart=bid.target_chart_part_one,
                    status='created'
                )
                bid_result.completed_chart = part_two_chart
                bid_result.save()
                
                allocated_charts.add(chart_id)
                
                if bid.bidder.id not in allocated_users:
                    allocated_users[bid.bidder.id] = []
                allocated_users[bid.bidder.id].append(chart_id)
            else:
                # 该谱面已被更高出价者获得，标记此竞标为drop
                bid.is_dropped = True
                bid.save()
        
        # 获取所有第一部分谱面（可参与竞标的对象）
        all_part_one_charts = Chart.objects.filter(is_part_one=True)
        all_chart_ids = set(chart.id for chart in all_part_one_charts)
        
        # 获取未被分配的一半谱面
        unallocated_charts = list(all_chart_ids - allocated_charts)
        
        # 第二阶段：对于未获得任何谱面的用户，随机分配
        bidding_users = set(bid.bidder.id for bid in all_bids)
        
        for user_id in bidding_users:
            if user_id not in allocated_users:
                # 用户未获得任何谱面，随机分配一个
                if unallocated_charts:
                    random_chart_id = random.choice(unallocated_charts)
                    random_chart = Chart.objects.get(id=random_chart_id)
                    
                    user = User.objects.get(id=user_id)
                    bid_result = SecondBidResult.objects.create(
                        second_bidding_round=second_bidding_round,
                        winner=user,
                        part_one_chart=random_chart,
                        bid_amount=0,
                        allocation_type='random'
                    )
                    
                    # 创建第二部分谱面
                    part_two_chart = Chart.objects.create(
                        bidding_round=second_bidding_round.first_bidding_round,
                        user=user,
                        song=random_chart.song,
                        is_part_one=False,
                        part_one_chart=random_chart,
                        status='created'
                    )
                    bid_result.completed_chart = part_two_chart
                    bid_result.save()
                    
                    unallocated_charts.remove(random_chart_id)
        
        # 标记轮次为已完成
        second_bidding_round.status = 'completed'
        second_bidding_round.completed_at = timezone.now()
        second_bidding_round.save()
        
        return {
            'total_bids': all_bids.count(),
            'allocated_charts': len(allocated_charts),
            'winners_count': len(allocated_users),
            'unallocated_charts': len(unallocated_charts)
        }
    
    @staticmethod
    def validate_second_bid(user, target_chart_part_one, amount):
        """
        验证第二轮竞标是否有效
        
        验证项：
        1. 用户是否有足够的剩余token
        2. 目标谱面是否是第一部分
        3. 目标谱面是否已经完成了第二部分
        4. 用户是否是目标谱面的创建者
        
        Args:
            user: 竞标用户
            target_chart_part_one: 目标的第一部分谱面
            amount: 竞标金额
            
        Returns:
            tuple: (is_valid, error_message)
        """
        from .models import BidResult, Chart
        
        # 验证目标谱面是否为第一部分
        if not target_chart_part_one.is_part_one:
            return False, '目标谱面必须是第一部分'
        
        # 验证目标谱面是否已经有第二部分完成
        second_part_exists = Chart.objects.filter(
            part_one_chart=target_chart_part_one,
            is_part_one=False,
            status__in=['submitted', 'reviewed']
        ).exists()
        
        if second_part_exists:
            return False, '该谱面的第二部分已完成，无法再次竞标'
        
        # 验证用户是否是目标谱面的创建者
        if target_chart_part_one.user == user:
            return False, '不能对自己的谱面进行竞标'
        
        # 验证用户的剩余token是否足够
        # 计算用户在第一轮中消耗的token
        first_round_spent = BidResult.objects.filter(
            bidding_round__id=target_chart_part_one.created_at.year  # 使用年份作为示例，实际应该从上下文获取
        ).aggregate(
            total_spent=Sum('bid_amount')
        )['total_spent'] or 0
        
        # 这里简化处理，实际应该追踪用户的token使用情况
        try:
            user_profile = user.userprofile
        except:
            user_profile = UserProfile.objects.get(user=user)
        
        if amount > user_profile.token:
            return False, '剩余token不足'
        
        return True, ''
    
    @staticmethod
    def get_available_part_one_charts(second_bidding_round, user=None):
        """
        获取可参与第二轮竞标的第一部分谱面列表
        
        可竞标的谱面需要满足：
        1. 是第一部分谱面
        2. 没有完成的第二部分
        3. 不是竞标用户自己创建的
        
        Args:
            second_bidding_round: 第二轮竞标轮次
            user: 竞标用户（用于过滤自己的谱面）
            
        Returns:
            QuerySet: 可竞标的第一部分谱面
        """
        from .models import Chart
        from django.db.models import Q, OuterRef, Exists
        
        # 获取所有已完成的第一部分谱面
        available_charts = Chart.objects.filter(
            is_part_one=True,
            status__in=['submitted', 'reviewed']
        )
        
        # 排除已有完成的第二部分的谱面
        part_two_exists = Chart.objects.filter(
            part_one_chart=OuterRef('pk'),
            is_part_one=False,
            status__in=['submitted', 'reviewed']
        )
        available_charts = available_charts.exclude(Exists(part_two_exists))
        
        # 排除用户自己创建的谱面
        if user:
            available_charts = available_charts.exclude(user=user)
        
        return available_charts.select_related('user', 'song').order_by('-average_score', '-created_at')
    
    @staticmethod
    def get_second_bid_results(user, second_bidding_round):
        """
        获取用户在某个第二轮竞标中的分配结果
        
        Args:
            user: 用户对象
            second_bidding_round: 第二轮竞标轮次
            
        Returns:
            QuerySet: 用户的第二轮竞标结果
        """
        from .models import SecondBidResult
        
        return SecondBidResult.objects.filter(
            second_bidding_round=second_bidding_round,
            winner=user
        ).select_related('part_one_chart', 'part_one_chart__user', 'part_one_chart__song', 'completed_chart')