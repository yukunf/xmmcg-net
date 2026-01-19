"""
测试互评系统对两部分合作谱面的支持
验证评分者不会被分配到自己参与的任何谱面（第一部分作者或第二部分续写者）
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.contrib.auth.models import User
from songs.models import (
    BiddingRound, Song, Chart, 
    PeerReviewAllocation, BidResult
)
from songs.bidding_service import PeerReviewService


def test_multi_chart_allocation():
    """测试两部分合作谱面场景下的互评分配"""
    
    print("=" * 60)
    print("测试场景：两部分合作谱面的互评分配")
    print("=" * 60)
    
    # 1. 创建测试竞标轮次
    round_obj, created = BiddingRound.objects.get_or_create(
        name='测试互评轮次-合作谱面',
        defaults={
            'bidding_type': 'song',
            'status': 'completed'
        }
    )
    print(f"\n✓ 竞标轮次: {round_obj.name} (ID: {round_obj.id})")
    
    # 2. 创建测试用户（12个用户）
    users = []
    for i in range(1, 13):
        user, _ = User.objects.get_or_create(
            username=f'user_{i}',
            defaults={'email': f'user{i}@test.com'}
        )
        users.append(user)
    
    print(f"\n✓ 创建/获取 {len(users)} 个测试用户")
    
    # 3. 创建合作谱面场景
    # 场景：12个用户，形成6对合作关系，每对创作2张完整谱面
    # - 用户1+用户2 合作创作2张谱面
    # - 用户3+用户4 合作创作2张谱面
    # - 用户5+用户6 合作创作2张谱面
    # - 用户7+用户8 合作创作2张谱面
    # - 用户9+用户10 合作创作2张谱面
    # - 用户11+用户12 合作创作2张谱面
    # 总共12张完整谱面，每张有2个贡献者
    
    songs = []
    charts = []
    
    for pair_idx in range(6):  # 6对合作关系
        first_user = users[pair_idx * 2]      # 第一部分作者
        second_user = users[pair_idx * 2 + 1]  # 第二部分作者
        
        for chart_idx in range(1, 3):  # 每对创作2张谱面
            # 创建歌曲
            song, _ = Song.objects.get_or_create(
                user=first_user,
                title=f'合作谱面_第{pair_idx+1}对_歌曲{chart_idx}',
                defaults={
                    'audio_hash': f'hash_{pair_idx}_{chart_idx}',
                    'file_size': 1024000,
                }
            )
            songs.append(song)
            
            # 创建第一部分竞标结果
            first_bid_result, _ = BidResult.objects.get_or_create(
                bidding_round=round_obj,
                user=first_user,
                song=song,
                defaults={
                    'bid_type': 'song',
                    'bid_amount': 100,
                    'allocation_type': 'bid_won'
                }
            )
            
            # 创建第二部分竞标结果（续写者）
            second_bid_result, _ = BidResult.objects.get_or_create(
                bidding_round=round_obj,
                user=second_user,
                song=song,
                defaults={
                    'bid_type': 'chart',  # 竞标谱面续写
                    'bid_amount': 50,
                    'allocation_type': 'bid_won'
                }
            )
            
            # 创建完整谱面（由两个人合作完成）
            chart, _ = Chart.objects.get_or_create(
                bidding_round=round_obj,
                user=first_user,  # 第一部分作者
                song=song,
                bid_result=first_bid_result,
                defaults={
                    'status': 'submitted',
                    'designer': f'{first_user.username}+{second_user.username}',
                    'completion_bid_result': second_bid_result,  # 第二部分作者
                }
            )
            
            # 如果已存在但没有设置第二部分，更新之
            if not chart.completion_bid_result:
                chart.completion_bid_result = second_bid_result
                chart.designer = f'{first_user.username}+{second_user.username}'
                chart.save()
            
            charts.append(chart)
    
    print(f"✓ 创建/获取 {len(songs)} 首歌曲")
    print(f"✓ 创建/获取 {len(charts)} 张合作谱面")
    
    # 4. 显示合作关系
    print("\n" + "=" * 60)
    print("谱面合作关系:")
    print("=" * 60)
    for chart in charts:
        first_author = chart.user.username
        second_author = chart.completion_bid_result.user.username if chart.completion_bid_result else "无"
        print(f"谱面 ID:{chart.id} - {chart.song.title}")
        print(f"  第一部分: {first_author}")
        print(f"  第二部分: {second_author}")
        print(f"  贡献者: {first_author} + {second_author}")
        print()
    
    # 6. 执行互评分配
    print("\n" + "=" * 60)
    print("开始执行互评分配...")
    print("=" * 60)
    
    # 清理已有的分配记录
    PeerReviewAllocation.objects.filter(bidding_round=round_obj).delete()
    print("✓ 已清理旧的分配记录")
    
    try:
        result = PeerReviewService.allocate_peer_reviews(
            bidding_round_id=round_obj.id,
            reviews_per_user=8  # 每人评8张谱面
        )
        
        print("\n✓ 分配成功！")
        print(f"  - 总分配数: {result['total_allocations']}")
        print(f"  - 谱面数: {result['charts_count']}")
        print(f"  - 评分者数: {result['reviewers_count']}")
        print(f"  - 每谱面评分数: {result['reviews_per_chart']}")
        print(f"  - 每评分者任务数: {result['tasks_per_reviewer']}")
        
    except Exception as e:
        print(f"\n✗ 分配失败: {str(e)}")
        return False
    
    # 7. 验证分配结果
    print("\n" + "=" * 60)
    print("验证分配结果:")
    print("=" * 60)
    
    all_valid = True
    expected_tasks_per_user = 8  # 每人评8张谱面
    expected_reviews_per_chart = 8  # 每张谱面被评8次
    
    # 验证1: 每个用户的任务数
    print(f"\n1. 验证每个用户恰好有{expected_tasks_per_user}个评分任务:")
    for user in users:
        task_count = PeerReviewAllocation.objects.filter(
            bidding_round=round_obj,
            reviewer=user
        ).count()
        
        status = "✓" if task_count == expected_tasks_per_user else "✗"
        print(f"  {status} {user.username}: {task_count} 个任务")
        
        if task_count != expected_tasks_per_user:
            all_valid = False
    
    # 验证2: 每张谱面的评分数
    print(f"\n2. 验证每张谱面恰好被评{expected_reviews_per_chart}次:")
    for chart in charts:
        review_count = PeerReviewAllocation.objects.filter(
            bidding_round=round_obj,
            chart=chart
        ).count()
        
        status = "✓" if review_count == expected_reviews_per_chart else "✗"
        print(f"  {status} {chart.song.title}: {review_count} 个评分")
        
        if review_count != expected_reviews_per_chart:
            all_valid = False
    
    # 验证3: 用户不评自己参与的任何谱面（核心验证 - 支持两部分合作）
    print("\n3. 验证用户不评自己参与的任何谱面（两部分合作场景）:")
    for user in users:
        # 获取该用户参与的所有谱面ID（作为第一部分作者或第二部分续写者）
        user_chart_ids = set()
        
        # 作为第一部分作者的谱面
        first_part_charts = Chart.objects.filter(
            bidding_round=round_obj,
            user=user
        ).values_list('id', flat=True)
        user_chart_ids.update(first_part_charts)
        
        # 作为第二部分续写者的谱面
        second_part_charts = Chart.objects.filter(
            bidding_round=round_obj,
            completion_bid_result__user=user
        ).values_list('id', flat=True)
        user_chart_ids.update(second_part_charts)
        
        # 获取分配给该用户的评分任务中的谱面ID
        assigned_chart_ids = set(PeerReviewAllocation.objects.filter(
            bidding_round=round_obj,
            reviewer=user
        ).values_list('chart_id', flat=True))
        
        # 检查是否有交集（如果有交集说明分配了自己参与的谱面）
        self_charts = user_chart_ids & assigned_chart_ids
        
        if self_charts:
            status = "✗"
            print(f"  {status} {user.username}: 被分配了自己参与的谱面! Chart IDs: {self_charts}")
            all_valid = False
        else:
            status = "✓"
            participated_count = len(user_chart_ids)
            print(f"  {status} {user.username}: 未被分配到自己参与的{participated_count}张谱面")
    
    # 验证4: 详细查看某个用户的分配情况
    print("\n4. 示例：查看第一对合作者的详细分配:")
    test_user1 = users[0]
    test_user2 = users[1]
    
    # 他们共同参与的谱面
    shared_charts = Chart.objects.filter(
        bidding_round=round_obj,
        user=test_user1,
        completion_bid_result__user=test_user2
    )
    
    print(f"\n  {test_user1.username} + {test_user2.username} 合作的谱面:")
    for chart in shared_charts:
        print(f"  - Chart ID:{chart.id} - {chart.song.title}")
    
    print(f"\n  {test_user1.username} 需要评分的谱面:")
    allocations1 = PeerReviewAllocation.objects.filter(
        bidding_round=round_obj,
        reviewer=test_user1
    ).select_related('chart', 'chart__user', 'chart__song', 'chart__completion_bid_result__user')
    
    for alloc in allocations1:
        contributors = [alloc.chart.user.username]
        if alloc.chart.completion_bid_result:
            contributors.append(alloc.chart.completion_bid_result.user.username)
        contributors_str = " + ".join(contributors)
        print(f"  - Chart ID:{alloc.chart.id} - {alloc.chart.song.title} (作者: {contributors_str})")
    
    print(f"\n  {test_user2.username} 需要评分的谱面:")
    allocations2 = PeerReviewAllocation.objects.filter(
        bidding_round=round_obj,
        reviewer=test_user2
    ).select_related('chart', 'chart__user', 'chart__song', 'chart__completion_bid_result__user')
    
    for alloc in allocations2:
        contributors = [alloc.chart.user.username]
        if alloc.chart.completion_bid_result:
            contributors.append(alloc.chart.completion_bid_result.user.username)
        contributors_str = " + ".join(contributors)
        print(f"  - Chart ID:{alloc.chart.id} - {alloc.chart.song.title} (作者: {contributors_str})")
    
    # 最终结果
    print("\n" + "=" * 60)
    if all_valid:
        print("✓✓✓ 所有验证通过！互评分配正确支持两部分合作谱面场景 ✓✓✓")
    else:
        print("✗✗✗ 验证失败！存在分配错误 ✗✗✗")
    print("=" * 60)
    
    return all_valid


if __name__ == '__main__':
    success = test_multi_chart_allocation()
    exit(0 if success else 1)
