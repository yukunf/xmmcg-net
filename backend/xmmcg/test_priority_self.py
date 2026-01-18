"""
测试 priority_self 功能
验证谱面竞标中，落选用户优先分配自己的半成品谱面

测试场景：
1. 第一轮：歌曲竞标，5个用户竞标5首歌
2. 用户提交半成品谱面（part_submitted状态）
3. 第二轮：谱面竞标，只有3个用户高价竞标3个谱面
4. 执行分配时 priority_self=True
5. 验证：落选的2个用户应该优先获得自己的半成品谱面

使用方法：
    python test_priority_self.py
"""

import os
import sys
import django
from django.core.files.base import ContentFile
from io import BytesIO

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.contrib.auth.models import User
from songs.models import Song, BiddingRound, Bid, BidResult, Chart
from songs.bidding_service import BiddingService
from users.models import UserProfile
from datetime import datetime, timedelta
from django.utils import timezone


def clear_test_data():
    """清除测试数据"""
    print("=" * 60)
    print("清除旧的测试数据...")
    print("=" * 60)
    
    test_users = User.objects.filter(username__startswith='priority_test_')
    
    # 清除关联数据
    Chart.objects.filter(user__in=test_users).delete()
    BidResult.objects.filter(user__in=test_users).delete()
    Bid.objects.filter(user__in=test_users).delete()
    Song.objects.filter(user__in=test_users).delete()
    
    # 清除竞标轮次
    BiddingRound.objects.filter(name__startswith='Priority测试').delete()
    
    # 清除用户
    UserProfile.objects.filter(user__in=test_users).delete()
    test_users.delete()
    
    print("✓ 测试数据已清除\n")


def create_test_users(count=5):
    """创建测试用户"""
    print(f"创建 {count} 个测试用户...")
    users = []
    
    for i in range(1, count + 1):
        username = f'priority_test_user{i}'
        user = User.objects.create_user(
            username=username,
            email=f'{username}@test.com',
            password='test123'
        )
        
        # 创建用户资料，给足够的代币
        profile = UserProfile.objects.create(
            user=user,
            token=200  # 足够的代币
        )
        
        users.append(user)
        print(f"  ✓ {username} (代币: {profile.token})")
    
    print(f"✓ 已创建 {len(users)} 个用户\n")
    return users


def create_first_round_songs(users):
    """第一轮：创建歌曲竞标轮次"""
    print("=" * 60)
    print("第一轮：歌曲竞标")
    print("=" * 60)
    
    # 创建歌曲
    print(f"创建 {len(users)} 首歌曲...")
    songs = []
    for i, user in enumerate(users, 1):
        # 创建一个虚拟的音频文件
        audio_data = b'fake audio data for testing'
        audio_content = ContentFile(audio_data, name=f'song{i}.mp3')
        
        song = Song.objects.create(
            user=user,
            title=f'测试歌曲{i}',
            audio_file=audio_content,
            file_size=len(audio_data),
            netease_url=f'https://music.163.com/song/{i}'
        )
        songs.append(song)
        print(f"  ✓ {song.title} (上传者: {user.username})")
    
    # 创建第一轮竞标轮次
    round1 = BiddingRound.objects.create(
        name='Priority测试-第一轮歌曲竞标',
        bidding_type='song',
        status='active'
    )
    print(f"\n✓ 创建竞标轮次: {round1.name}")
    
    # 每个用户竞标一首不同的歌（保证都能中标）
    print("\n用户竞标情况:")
    for i, user in enumerate(users):
        song = songs[i]  # 每人竞标一首不同的歌
        bid = Bid.objects.create(
            bidding_round=round1,
            user=user,
            bid_type='song',
            song=song,
            amount=50
        )
        print(f"  {user.username} 竞标 {song.title} (出价: {bid.amount})")
    
    # 执行分配
    print("\n执行第一轮竞标分配...")
    result = BiddingService.allocate_bids(round1.id, priority_self=False)
    print(f"✓ 分配完成: {result['winners']} 个中标者")
    
    # 显示分配结果
    print("\n第一轮分配结果:")
    for user in users:
        bid_result = BidResult.objects.filter(bidding_round=round1, user=user).first()
        if bid_result:
            print(f"  {user.username} → {bid_result.song.title}")
    
    print()
    return round1, songs


def submit_part_charts(users, round1):
    """用户提交半成品谱面"""
    print("=" * 60)
    print("用户提交半成品谱面")
    print("=" * 60)
    
    charts = []
    for user in users:
        # 获取用户的中标结果
        bid_result = BidResult.objects.filter(bidding_round=round1, user=user).first()
        if not bid_result:
            continue
        
        # 创建虚拟的maidata文件
        maidata_content = ContentFile(
            b'&title=test\n&artist=test\n&des=test\n',
            name=f'maidata_{user.username}.txt'
        )
        
        # 创建半成品谱面
        chart = Chart.objects.create(
            bidding_round=round1,
            user=user,
            song=bid_result.song,
            designer=f'{user.username}_designer',
            chart_file=maidata_content,
            status='part_submitted',  # 半成品状态
            is_part_one=True
        )
        charts.append(chart)
        print(f"  ✓ {user.username} 提交了《{bid_result.song.title}》的半成品谱面")
    
    print(f"\n✓ 已提交 {len(charts)} 个半成品谱面\n")
    return charts


def create_second_round_chart_bidding(users, charts):
    """第二轮：谱面竞标（故意让部分用户落选）"""
    print("=" * 60)
    print("第二轮：谱面竞标")
    print("=" * 60)
    
    # 创建谱面竞标轮次
    round2 = BiddingRound.objects.create(
        name='Priority测试-第二轮谱面竞标',
        bidding_type='chart',
        status='active'
    )
    print(f"创建竞标轮次: {round2.name}")
    print(f"可竞标谱面数: {len(charts)}")
    
    # 设计竞标策略：确保user4和user5落选且他们的谱面未被竞标
    # user1-3高价竞标谱面1,2,3 (都能中标)
    # user4和user5也竞标谱面1,2但价格低于user1-2 (会落选)
    # 谱面4和5不被任何人竞标，保留给user4和user5
    print("\n用户竞标情况:")
    print("策略: user1-3高价竞标谱面1,2,3，user4-5低价竞标谱面1,2（会落选）\n")
    print("谱面4和5不被竞标，留给user4和user5优先分配\n")
    
    # user1竞标谱面1，高价
    bid = Bid.objects.create(
        bidding_round=round2,
        user=users[0],
        bid_type='chart',
        chart=charts[0],  # 谱面1
        amount=80
    )
    print(f"  {users[0].username} 高价竞标 {charts[0].song.title} (作者: {charts[0].user.username}, 出价: 80)")
    
    # user2竞标谱面2，高价
    bid = Bid.objects.create(
        bidding_round=round2,
        user=users[1],
        bid_type='chart',
        chart=charts[1],  # 谱面2
        amount=80
    )
    print(f"  {users[1].username} 高价竞标 {charts[1].song.title} (作者: {charts[1].user.username}, 出价: 80)")
    
    # user3竞标谱面3，高价
    bid = Bid.objects.create(
        bidding_round=round2,
        user=users[2],
        bid_type='chart',
        chart=charts[2],  # 谱面3
        amount=80
    )
    print(f"  {users[2].username} 高价竞标 {charts[2].song.title} (作者: {charts[2].user.username}, 出价: 80)")
    
    # user4低价竞标谱面1（会被user1的高价击败）
    bid = Bid.objects.create(
        bidding_round=round2,
        user=users[3],
        bid_type='chart',
        chart=charts[0],  # 谱面1，和user1竞争
        amount=1
    )
    print(f"  {users[3].username} 低价竞标 {charts[0].song.title} (作者: {charts[0].user.username}, 出价: 1) → 将落选")
    
    # user5低价竞标谱面2（会被user2的高价击败）
    bid = Bid.objects.create(
        bidding_round=round2,
        user=users[4],
        bid_type='chart',
        chart=charts[1],  # 谱面2，和user2竞争
        amount=1
    )
    print(f"  {users[4].username} 低价竞标 {charts[1].song.title} (作者: {charts[1].user.username}, 出价: 1) → 将落选")
    
    print(f"\n预期结果: user4和user5落选后，将被优先分配到自己的谱面（谱面4和谱面5）")
    
    return round2


def allocate_with_priority_self(round2, users, charts):
    """执行分配并验证priority_self功能"""
    print("\n" + "=" * 60)
    print("执行谱面竞标分配 (priority_self=True)")
    print("=" * 60)
    
    # 执行分配
    result = BiddingService.allocate_bids(round2.id, priority_self=True)
    
    print(f"\n分配统计:")
    print(f"  总谱面数: {result['total_targets']}")
    print(f"  已分配: {result['allocated_targets']}")
    print(f"  中标者: {result['winners']}")
    print(f"  竞标者: {result['total_bidders']}")
    
    # 显示分配结果
    print("\n" + "=" * 60)
    print("分配结果验证")
    print("=" * 60)
    
    # 先显示未分配的谱面
    unallocated_chart_ids = []
    for chart in charts:
        if not BidResult.objects.filter(bidding_round=round2, chart=chart).exists():
            unallocated_chart_ids.append(chart.id)
    
    print(f"\n未分配的谱面: {len(unallocated_chart_ids)} 个")
    for chart_id in unallocated_chart_ids:
        chart = Chart.objects.get(id=chart_id)
        print(f"  - {chart.song.title} (作者: {chart.user.username}, ID: {chart.id})")
    
    success = True
    
    for user in users:
        bid_result = BidResult.objects.filter(bidding_round=round2, user=user).first()
        if bid_result:
            chart = bid_result.chart
            is_own_chart = (chart.user == user)
            allocation_type = bid_result.allocation_type
            
            # 找出该用户自己的谱面
            own_chart = Chart.objects.filter(user=user, status='part_submitted').first()
            
            print(f"\n{user.username}:")
            print(f"  分配方式: {allocation_type}")
            print(f"  获得谱面: {chart.song.title} (原作者: {chart.user.username})")
            print(f"  是否是自己的谱面: {'是 ✓' if is_own_chart else '否'}")
            
            # 验证逻辑
            if allocation_type == 'random':
                if own_chart and not is_own_chart:
                    print(f"  ⚠️  警告: 该用户有自己的谱面《{own_chart.song.title}》但被分配了别人的谱面!")
                    success = False
                elif own_chart and is_own_chart:
                    print(f"  ✓ 正确: 随机分配优先分配了自己的谱面")
                elif not own_chart:
                    print(f"  ✓ 正确: 该用户没有自己的未分配谱面，分配了其他谱面")
        else:
            print(f"\n{user.username}: 未获得分配")
    
    print("\n" + "=" * 60)
    if success:
        print("✓✓✓ 测试通过！priority_self 功能工作正常 ✓✓✓")
    else:
        print("✗✗✗ 测试失败！请检查 priority_self 逻辑 ✗✗✗")
    print("=" * 60)
    
    return success


def main():
    """主测试流程"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "     Priority_Self 功能测试".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 清除旧数据
    clear_test_data()
    
    # 创建用户
    users = create_test_users(5)
    
    # 第一轮：歌曲竞标
    round1, songs = create_first_round_songs(users)
    
    # 提交半成品谱面
    charts = submit_part_charts(users, round1)
    
    # 第二轮：谱面竞标
    round2 = create_second_round_chart_bidding(users, charts)
    
    # 执行分配并验证
    success = allocate_with_priority_self(round2, users, charts)
    
    print("\n测试完成！\n")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
