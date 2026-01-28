"""
竞标分配测试脚本
用于生成测试数据并验证竞标分配逻辑

测试场景：
1. 多人同价竞标同一首歌（验证随机分配）
2. 部分用户竞标策略导致落选（验证保底随机分配）
3. 不同价格竞标（验证价高者得）

使用方法：
    python test_bidding_allocation.py
"""

import os
import sys
import django
import uuid
from django.core.files.base import ContentFile

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.contrib.auth.models import User
from songs.models import Song, BiddingRound, Bid, BidResult
from songs.bidding_service import BiddingService
from users.models import UserProfile
from datetime import datetime, timedelta
from django.utils import timezone


def clear_test_data():
    """清除之前的测试数据"""
    print("正在清除旧的测试数据...")
    
    # 清除测试用户的竞标相关数据
    test_users = User.objects.filter(username__startswith='bidtest_')
    BidResult.objects.filter(user__in=test_users).delete()
    Bid.objects.filter(user__in=test_users).delete()
    Song.objects.filter(user__in=test_users).delete()
    
    # 清除测试竞标轮次
    BiddingRound.objects.filter(name__startswith='测试竞标轮次').delete()
    
    # 清除测试用户
    test_users.delete()
    
    print("✓ 测试数据已清除\n")


def create_test_users(count=10):
    """创建测试用户"""
    print(f"正在创建 {count} 个测试用户...")
    users = []
    
    for i in range(1, count + 1):
        username = f'bidtest_{i}'
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
            }
        )
        if created:
            user.set_password('test123')
            user.save()
        
        # 创建用户资料并设置代币
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'qqid' : f'{100000 + i}'})
        profile.token = 500  # 给足够的代币进行测试
        profile.save()
        
        users.append(user)
        print(f"  ✓ {username} (代币: {profile.token})")
    
    print(f"✓ 成功创建 {len(users)} 个测试用户\n")
    return users


def create_test_songs(users):
    """创建测试歌曲（每个用户上传1-2首）"""
    print("正在创建测试歌曲...")
    songs = []
    
    song_titles = [
        "测试歌曲 - 热门曲目A",
        "测试歌曲 - 热门曲目B", 
        "测试歌曲 - 冷门曲目C",
        "测试歌曲 - 普通曲目D",
        "测试歌曲 - 普通曲目E",
    ]
    
    for i, title in enumerate(song_titles):
        # 前5个用户各上传一首歌
        if i < len(users):
            # 先创建基础记录（不包含文件），随后保存一个占位音频文件
            song = Song(
                user=users[i],
                title=title,
                audio_hash=f'test_hash_{uuid.uuid4().hex}',  # 生成唯一哈希
                file_size=3000000,  # 假设3MB文件大小
            )
            song.save()
            # 保存一个占位音频文件到 FileField（满足非空约束）
            dummy_audio = ContentFile(b"test audio content")
            song.audio_file.save("dummy.mp3", dummy_audio, save=True)
            songs.append(song)
            print(f"  ✓ {title} (上传者: {users[i].username})")
    
    print(f"✓ 成功创建 {len(songs)} 首测试歌曲\n")
    return songs


def create_bidding_round():
    """创建测试竞标轮次"""
    print("正在创建竞标轮次...")
    
    bidding_round = BiddingRound.objects.create(
        name=f'测试竞标轮次 - {datetime.now().strftime("%Y%m%d_%H%M%S")}',
        status='active',
        bidding_type='song',  # 统一模型下显式指定为歌曲竞标
        started_at=timezone.now()
    )
    
    print(f"✓ 竞标轮次已创建: {bidding_round.name}\n")
    return bidding_round


def create_test_bids(users, songs, bidding_round):
    """
    创建测试竞标数据
    
    场景设计：
    - 歌曲A: 5人同价(300)竞标 → 随机分配1人中标，4人落选
    - 歌曲B: 3人不同价竞标 (400, 300, 200) → 价高者中标
    - 歌曲C: 2人竞标 (250, 250) → 同价随机
    - 歌曲D: 1人竞标 (150) → 直接中标
    - 歌曲E: 无人竞标 → 随机分配给未中标用户
    
    用户6-10: 只竞标少量歌曲，确保部分人落选触发保底分配
    """
    print("正在创建竞标数据...\n")
    
    bids_data = [
        # === 场景1: 歌曲A - 5人同价竞标 (测试同价随机) ===
        {"user": users[0], "song": songs[0], "amount": 300, "delay": 0},
        {"user": users[1], "song": songs[0], "amount": 300, "delay": 1},
        {"user": users[2], "song": songs[0], "amount": 300, "delay": 2},
        {"user": users[3], "song": songs[0], "amount": 300, "delay": 3},
        {"user": users[4], "song": songs[0], "amount": 300, "delay": 4},
        
        # === 场景2: 歌曲B - 不同价竞标 (测试价高者得) ===
        {"user": users[5], "song": songs[1], "amount": 400, "delay": 0},
        {"user": users[6], "song": songs[1], "amount": 300, "delay": 1},
        {"user": users[7], "song": songs[1], "amount": 200, "delay": 2},
        
        # === 场景3: 歌曲C - 2人同价 (测试同价随机) ===
        {"user": users[8], "song": songs[2], "amount": 250, "delay": 0},
        {"user": users[9], "song": songs[2], "amount": 250, "delay": 1},
        
        # === 场景4: 歌曲D - 单人竞标 (直接中标) ===
        {"user": users[1], "song": songs[3], "amount": 150, "delay": 0},
        
        # === 场景5: 歌曲E - 无人竞标 (会被随机分配) ===
        # 不创建竞标
        
        # === 额外竞标：让部分用户有多个竞标但策略不佳 ===
        {"user": users[2], "song": songs[1], "amount": 100, "delay": 5},  # 出价太低
        {"user": users[3], "song": songs[2], "amount": 100, "delay": 5},  # 出价太低
    ]
    
    base_time = timezone.now()
    
    print("场景说明：")
    print("=" * 60)
    print("场景1 - 歌曲A (热门曲目A):")
    print("  → 5人同价300竞标，不同时间提交")
    print("  → 预期：随机选1人中标，其余4人落选\n")
    
    print("场景2 - 歌曲B (热门曲目B):")
    print("  → 3人不同价竞标 (400, 300, 200)")
    print("  → 预期：出价400的用户中标\n")
    
    print("场景3 - 歌曲C (冷门曲目C):")
    print("  → 2人同价250竞标")
    print("  → 预期：随机选1人中标\n")
    
    print("场景4 - 歌曲D (普通曲目D):")
    print("  → 1人竞标150")
    print("  → 预期：直接中标\n")
    
    print("场景5 - 歌曲E (普通曲目E):")
    print("  → 无人竞标")
    print("  → 预期：随机分配给未中标用户（需扣除200代币）\n")
    
    print("=" * 60)
    print("\n创建竞标记录：")
    
    for bid_info in bids_data:
        # 设置不同的创建时间（模拟不同时间提交）
        created_time = base_time + timedelta(seconds=bid_info['delay'])
        
        # 使用统一服务创建竞标，确保通过新校验逻辑
        bid = BiddingService.create_bid(
            user=bid_info['user'],
            bidding_round=bidding_round,
            amount=bid_info['amount'],
            song=bid_info['song'],
        )
        # 手动设置创建时间（仅用于测试）
        Bid.objects.filter(id=bid.id).update(created_at=created_time)
        
        print(f"  ✓ {bid_info['user'].username} → {bid_info['song'].title}: {bid_info['amount']}代币 (延迟{bid_info['delay']}秒)")
    
    total_bids = Bid.objects.filter(bidding_round=bidding_round).count()
    print(f"\n✓ 成功创建 {total_bids} 条竞标记录\n")


def run_allocation(bidding_round):
    """执行竞标分配"""
    print("=" * 60)
    print("执行竞标分配...")
    print("=" * 60 + "\n")
    
    try:
        BiddingService.allocate_bids(bidding_round.id)
        print("✓ 分配完成！\n")
    except Exception as e:
        print(f"✗ 分配失败: {str(e)}\n")
        return False
    
    return True


def show_results(bidding_round):
    """显示分配结果"""
    print("=" * 60)
    print("分配结果")
    print("=" * 60 + "\n")
    
    results = BidResult.objects.filter(bidding_round=bidding_round).select_related('user', 'song', 'chart', 'chart__user')
    
    # 按分配类型分组
    win_results = results.filter(allocation_type='win')
    random_results = results.filter(allocation_type='random')
    
    print(f"【竞价中标】共 {win_results.count()} 人：")
    print("-" * 60)
    for result in win_results:
        if result.bid_type == 'song' and result.song:
            target_text = result.song.title
        elif result.bid_type == 'chart' and result.chart:
            target_text = f"{result.chart.user.username} 的谱面（{result.chart.song.title}）"
        else:
            target_text = "未知标的"
        print(f"  {result.user.username} → {target_text}")
        print(f"    出价: {result.bid_amount} 代币 | 类型: {result.allocation_type}")
    
    print(f"\n【保底随机分配】共 {random_results.count()} 人：")
    print("-" * 60)
    for result in random_results:
        if result.bid_type == 'song' and result.song:
            target_text = result.song.title
        elif result.bid_type == 'chart' and result.chart:
            target_text = f"{result.chart.user.username} 的谱面（{result.chart.song.title}）"
        else:
            target_text = "未知标的"
        print(f"  {result.user.username} → {target_text}")
        print(f"    扣除代币: {result.bid_amount} | 类型: {result.allocation_type}")
    
    print("\n" + "=" * 60)
    
    # 显示用户代币变化
    print("用户代币余额：")
    print("-" * 60)
    test_users = User.objects.filter(username__startswith='bidtest_')
    for user in test_users:
        profile = UserProfile.objects.get(user=user)
        has_target = results.filter(user=user).exists()
        status = "✓ 已分配标的" if has_target else "✗ 未分配"
        print(f"  {user.username}: {profile.token} 代币 [{status}]")
    
    print("\n" + "=" * 60)
    
    # 统计信息
    print("统计信息：")
    print("-" * 60)
    total_users = test_users.count()
    allocated_users = results.values('user').distinct().count()
    print(f"  参与用户: {total_users}")
    print(f"  已分配用户: {allocated_users}")
    print(f"  未分配用户: {total_users - allocated_users}")
    print(f"  总歌曲数: {Song.objects.filter(user__username__startswith='bidtest_').count()}")
    print(f"  已分配歌曲: {results.count()}")
    print(f"  竞价中标: {win_results.count()}")
    print(f"  保底分配: {random_results.count()}")
    
    print("\n" + "=" * 60 + "\n")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("竞标分配测试脚本")
    print("=" * 60 + "\n")
    
    # 步骤1: 清除旧数据
    clear_test_data()
    
    # 步骤2: 创建测试用户
    users = create_test_users(count=10)
    
    # 步骤3: 创建测试歌曲
    songs = create_test_songs(users)
    
    # 步骤4: 创建竞标轮次
    bidding_round = create_bidding_round()
    
    # 步骤5: 创建竞标数据
    create_test_bids(users, songs, bidding_round)
    
    # 步骤6: 执行分配
    success = run_allocation(bidding_round)
    
    # 步骤7: 显示结果
    if success:
        show_results(bidding_round)
        
        print("测试完成！")
        print("\n提示：")
        print("  1. 可访问 Django Admin 查看详细数据")
        print("  2. 竞标轮次ID:", bidding_round.id)
        print("  3. 测试用户: bidtest_1 ~ bidtest_10 (密码: test123)")
        print("  4. 重新运行此脚本会清除并重新生成数据")
    else:
        print("测试失败，请检查错误信息")


if __name__ == '__main__':
    main()
