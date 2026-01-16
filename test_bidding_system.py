"""
竞标系统测试用例

测试完整的竞标流程：
1. 创建用户并上传歌曲
2. 创建竞标轮次
3. 用户创建竞标
4. Admin 执行分配
5. 验证分配结果
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from songs.models import Song, BiddingRound, Bid, BidResult, MAX_SONGS_PER_USER, MAX_BIDS_PER_USER
from users.models import UserProfile
from songs.bidding_service import BiddingService


def print_section(title):
    """打印分隔符"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_bidding_system():
    """测试竞标系统完整流程"""
    
    print_section("竞标系统测试")
    
    # 清理之前的测试数据（可选）
    print("准备测试环境...")
    
    # 1. 创建测试用户
    print_section("第一步：创建测试用户")
    
    users = []
    for i in range(1, 5):
        username = f"bidder{i}"
        try:
            user = User.objects.get(username=username)
            print(f"  用户 {username} 已存在")
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=username,
                password='password123',
                email=f'{username}@test.com'
            )
            # 创建用户资料
            UserProfile.objects.create(user=user, token=10000)  # 每个用户 10000 代币
            print(f"  ✓ 创建用户 {username}，初始代币: 10000")
        
        users.append(user)
    
    # 创建 admin 用户
    try:
        admin = User.objects.get(username='admin_test')
    except User.DoesNotExist:
        admin = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='admin123'
        )
        UserProfile.objects.create(user=admin, token=0)
        print(f"  ✓ 创建管理员用户 admin_test")
    
    # 2. 上传歌曲
    print_section("第二步：用户上传歌曲")
    
    songs = []
    for i, user in enumerate(users, start=1):
        # 每个用户上传 1-2 首歌曲
        for j in range(1 if i % 2 == 0 else 2):
            # 注意：此测试需要真实的音频文件，这里仅演示逻辑
            # 实际使用时需要提供真实的文件
            print(f"  ℹ 用户 {user.username} 上传第 {j} 首歌曲")
            print(f"    （本测试中跳过实际文件上传，仅演示数据库操作）")
    
    # 手动创建测试歌曲（跳过文件验证）
    test_songs = []
    for i in range(1, 4):
        user = users[(i-1) % len(users)]
        song = Song.objects.create(
            user=user,
            title=f"Test Song {i}",
            audio_hash=f"hash{i}",
            file_size=1000000 * i,
        )
        test_songs.append(song)
        print(f"  ✓ 创建歌曲 '{song.title}' (上传者: {user.username}, ID: {song.id})")
    
    # 3. 创建竞标轮次
    print_section("第三步：创建竞标轮次")
    
    bidding_round = BiddingRound.objects.create(
        name="Test Bidding Round 001",
        status='active'
    )
    print(f"  ✓ 创建竞标轮次 '{bidding_round.name}'")
    print(f"    状态: {bidding_round.get_status_display()}")
    print(f"    可用歌曲: {len(test_songs)} 首")
    print(f"    每用户最多竞标: {MAX_BIDS_PER_USER} 首")
    
    # 4. 用户创建竞标
    print_section("第四步：用户创建竞标")
    
    bids_data = [
        # (用户索引, 歌曲索引, 出价金额)
        (0, 0, 800),   # 用户1 对歌曲1 出价 800
        (1, 0, 600),   # 用户2 对歌曲1 出价 600
        (1, 1, 700),   # 用户2 对歌曲2 出价 700
        (2, 1, 500),   # 用户3 对歌曲2 出价 500
        (3, 2, 400),   # 用户4 对歌曲3 出价 400
        (0, 1, 650),   # 用户1 对歌曲2 出价 650
    ]
    
    bids = []
    for user_idx, song_idx, amount in bids_data:
        user = users[user_idx]
        song = test_songs[song_idx]
        
        try:
            bid = BiddingService.create_bid(
                user=user,
                bidding_round=bidding_round,
                song=song,
                amount=amount
            )
            bids.append(bid)
            print(f"  ✓ {user.username} 对 '{song.title}' 竞标 {amount} 代币")
        except Exception as e:
            print(f"  ✗ {user.username} 竞标失败: {str(e)}")
    
    # 显示竞标摘要
    print(f"\n  竞标摘要:")
    print(f"  - 总竞标数: {len(bids)}")
    print(f"  - 参与用户: {len(set(b.user_id for b in bids))}")
    
    # 按歌曲分组显示竞标
    for song in test_songs:
        song_bids = [b for b in bids if b.song_id == song.id]
        if song_bids:
            print(f"\n  歌曲 '{song.title}' 的竞标:")
            for bid in sorted(song_bids, key=lambda b: -b.amount):
                print(f"    - {bid.user.username}: {bid.amount} 代币")
    
    # 5. 执行竞标分配
    print_section("第五步：执行竞标分配")
    
    print(f"  分配前状态:")
    print(f"  - 竞标轮次: {bidding_round.name}")
    print(f"  - 轮次状态: {bidding_round.get_status_display()}")
    print(f"  - 竞标数: {Bid.objects.filter(bidding_round=bidding_round).count()}")
    print(f"  - 已分配: {BidResult.objects.filter(bidding_round=bidding_round).count()}")
    
    try:
        result = BiddingService.allocate_bids(bidding_round.id)
        print(f"\n  ✓ 竞标分配完成!")
        print(f"\n  分配统计:")
        print(f"  - 总歌曲数: {result['total_songs']}")
        print(f"  - 已分配: {result['allocated_songs']}")
        print(f"  - 未分配: {result['unallocated_songs']}")
        print(f"  - 获胜者数: {result['winners']}")
        print(f"  - 参与用户数: {result['total_bidders']}")
    except Exception as e:
        print(f"  ✗ 分配失败: {str(e)}")
        return
    
    # 6. 验证分配结果
    print_section("第六步：验证分配结果")
    
    # 刷新轮次对象
    bidding_round.refresh_from_db()
    
    print(f"  轮次最终状态: {bidding_round.get_status_display()}")
    
    all_results = BidResult.objects.filter(bidding_round=bidding_round)
    print(f"  总分配数: {all_results.count()}\n")
    
    # 按用户分组显示结果
    for user in users:
        user_results = BidResult.objects.filter(bidding_round=bidding_round, user=user)
        if user_results.exists():
            print(f"  用户 {user.username}:")
            for result in user_results:
                allocation_type_display = dict(BidResult.ALLOCATION_TYPE_CHOICES)[result.allocation_type]
                print(f"    - 获得 '{result.song.title}' ({allocation_type_display}, {result.bid_amount} 代币)")
        else:
            print(f"  用户 {user.username}: 未获得任何歌曲")
    
    # 验证中标逻辑
    print(f"\n  中标验证:")
    
    # 对于歌曲1，最高出价应该是用户1的800代币
    song1_results = BidResult.objects.filter(
        bidding_round=bidding_round,
        song=test_songs[0],
        allocation_type='win'
    )
    if song1_results.exists():
        winner = song1_results.first()
        print(f"  ✓ 歌曲1 中标者: {winner.user.username} ({winner.bid_amount} 代币)")
        assert winner.user_id == users[0].id, "歌曲1 应该由用户1 中标"
        assert winner.bid_amount == 800, "歌曲1 中标价格应该是 800"
    else:
        print(f"  ✗ 歌曲1 没有中标者")
    
    # 对于歌曲2，最高出价应该是用户1的650代币
    song2_results = BidResult.objects.filter(
        bidding_round=bidding_round,
        song=test_songs[1],
        allocation_type='win'
    )
    if song2_results.exists():
        winner = song2_results.first()
        print(f"  ✓ 歌曲2 中标者: {winner.user.username} ({winner.bid_amount} 代币)")
        assert winner.user_id == users[0].id, "歌曲2 应该由用户1 中标"
        assert winner.bid_amount == 650, "歌曲2 中标价格应该是 650"
    else:
        print(f"  ✗ 歌曲2 没有中标者")
    
    # 7. 显示竞标被 drop 的情况
    print_section("第七步：验证被 drop 的竞标")
    
    dropped_bids = Bid.objects.filter(bidding_round=bidding_round, is_dropped=True)
    print(f"  被 drop 的竞标数: {dropped_bids.count()}\n")
    
    for bid in dropped_bids:
        print(f"  - {bid.user.username} 对 '{bid.song.title}' 的竞标已 drop (出价: {bid.amount})")
    
    # 8. 总结
    print_section("测试总结")
    
    print(f"  ✓ 竞标系统测试完成")
    print(f"\n  关键数据:")
    print(f"  - 上传歌曲: {Song.objects.count()} 首")
    print(f"  - 竞标轮次: {BiddingRound.objects.count()} 个")
    print(f"  - 竞标记录: {Bid.objects.count()} 条")
    print(f"  - 分配结果: {BidResult.objects.count()} 条")
    
    print(f"\n  配置常量:")
    print(f"  - MAX_SONGS_PER_USER: {MAX_SONGS_PER_USER} (每用户最多上传歌曲数)")
    print(f"  - MAX_BIDS_PER_USER: {MAX_BIDS_PER_USER} (每用户每轮最多竞标歌曲数)")


if __name__ == '__main__':
    test_bidding_system()
