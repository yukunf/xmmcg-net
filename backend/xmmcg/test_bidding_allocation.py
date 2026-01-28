"""
竞标分配与评分任务测试脚本 (分步骤交互式执行)
用于生成测试数据并验证竞标分配逻辑和评分任务分配逻辑

执行模式：
=== 交互式分步执行 ===
1. 自动执行：竞标→制谱 阶段
2. 用户选择：是否继续执行评分分配测试
3. 用户选择：是否继续执行评分提交模拟

测试场景：
=== 竞标测试 ===
1. 多人同价竞标同一首歌（验证随机分配）
2. 部分用户竞标策略导致落选（验证保底随机分配）
3. 不同价格竞标（验证价高者得）

=== 谱面创建测试 ===
4. 基于竞标结果自动创建完成稿谱面
5. 谱面状态设置为'已提交'，可用于评分

=== 评分测试（可选） ===
6. 自动分配评分任务（每人评分若干谱面）
7. 模拟用户提交评分（包含评分、评论、喜欢）
8. 统计评分完成情况和平均分

使用方法：
    python test_bidding_allocation.py

交互提示：
    - 竞标和制谱阶段会自动执行
    - 完成后会询问是否继续评分分配测试
    - 评分分配完成后会询问是否模拟评分提交
    - 每个阶段都可以选择停止并查看当前结果

注意：
    - 脚本会清除所有以 'bidtest_' 开头的用户数据
    - 测试用户密码统一为 'test123'
    - 建议在开发环境中运行此脚本
    - 可通过 Ctrl+C 随时中断脚本执行
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
from songs.models import Song, BiddingRound, Bid, BidResult, Chart, PeerReviewAllocation, PeerReview, PEER_REVIEW_MAX_SCORE
from songs.bidding_service import BiddingService, PeerReviewService
from users.models import UserProfile
from datetime import datetime, timedelta
from django.utils import timezone
import random


def clear_test_data():
    """清除之前的测试数据"""
    print("正在清除旧的测试数据...")
    
    # 清除测试用户的竞标相关数据
    test_users = User.objects.filter(username__startswith='bidtest_')
    
    # 清除评分相关数据
    PeerReview.objects.filter(reviewer__in=test_users).delete()
    PeerReviewAllocation.objects.filter(reviewer__in=test_users).delete()
    Chart.objects.filter(user__in=test_users).delete()
    
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
                'first_name': f'测试用户{i}'
            }
        )
        if created:
            user.set_password('test123')
            user.save()
        
        # 创建用户资料并设置代币
        profile, _ = UserProfile.objects.get_or_create(user=user)
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


def create_test_charts(users, songs, bidding_round):
    """创建测试谱面（基于竞标分配结果）"""
    print("正在创建测试谱面...")
    
    # 获取竞标分配结果
    results = BidResult.objects.filter(bidding_round=bidding_round).select_related('user', 'song')
    
    charts = []
    for result in results:
        # 为每个中标用户创建对应的谱面
        chart = Chart.objects.create(
            bidding_round=bidding_round,
            user=result.user,
            song=result.song,
            status='submitted',  # 设为已提交状态，可以被评分
            is_part_one=True,    # 假设都是第一部分谱面
        )
        charts.append(chart)
        print(f"  ✓ {result.user.username} → {result.song.title} 的谱面")
    
    print(f"\n✓ 成功创建 {len(charts)} 个测试谱面\n")
    return charts


def run_peer_review_allocation(bidding_round):
    """执行评分任务分配"""
    print("=" * 60)
    print("执行评分任务分配...")
    print("=" * 60 + "\n")
    
    # 获取谱面数和评分者数
    charts = Chart.objects.filter(bidding_round=bidding_round, status='submitted')
    num_charts = charts.count()
    
    # 计算合适的每人评分任务数
    # 考虑到用户不能评自己的谱面，我们需要调整参数
    if num_charts <= 0:
        print("  ✗ 没有可评分的谱面")
        return False
    
    # 对于测试场景，使用每人评4个任务（这样5个人×4个任务=20次评分，5个谱面每个被评4次）
    reviews_per_user = 4
    
    try:
        stats = PeerReviewService.allocate_peer_reviews(bidding_round.id, reviews_per_user=reviews_per_user)
        print(f"✓ 评分任务分配完成！")
        print(f"  - 总分配任务数: {stats.get('total_allocations', 0)}")
        print(f"  - 参与评分用户: {stats.get('reviewers_count', 0)}")
        print(f"  - 被评分谱面: {stats.get('charts_count', 0)}")
        print(f"  - 每人评分任务: {reviews_per_user} 个")
        print(f"  - 每谱面被评: 约 {reviews_per_user} 次\n")
        return True
    except Exception as e:
        print(f"✗ 评分任务分配失败: {str(e)}")
        
        # 如果4个任务仍然失败，尝试更小的数量
        print("  尝试降低每人评分任务数...")
        for reviews_per_user in [3, 2, 1]:
            try:
                print(f"  → 尝试每人评分 {reviews_per_user} 个任务...")
                stats = PeerReviewService.allocate_peer_reviews(bidding_round.id, reviews_per_user=reviews_per_user)
                print(f"✓ 评分任务分配成功！(每人{reviews_per_user}个任务)")
                print(f"  - 总分配任务数: {stats.get('total_allocations', 0)}")
                print(f"  - 参与评分用户: {stats.get('reviewers_count', 0)}")
                print(f"  - 被评分谱面: {stats.get('charts_count', 0)}\n")
                return True
            except Exception as e2:
                print(f"    ✗ 仍然失败: {str(e2)}")
                continue
        
        print("  ✗ 所有评分分配尝试都失败了\n")
        return False


def simulate_peer_reviews(bidding_round):
    """模拟用户提交评分"""
    print("=" * 60)
    print("模拟用户提交评分...")
    print("=" * 60 + "\n")
    
    allocations = PeerReviewAllocation.objects.filter(
        bidding_round=bidding_round,
        status='pending'
    ).select_related('reviewer', 'chart', 'chart__user', 'chart__song')
    
    submitted_count = 0
    total_count = allocations.count()
    
    print(f"共有 {total_count} 个评分任务需要完成\n")
    
    # 模拟80%的用户完成评分，20%不完成（测试现实情况）
    for allocation in allocations:
        # 80%概率提交评分
        if random.random() < 0.8:
            # 生成随机评分（偏向中等偏上的分数）
            if random.random() < 0.1:  # 10%概率给低分
                score = random.randint(10, 25)
            elif random.random() < 0.3:  # 30%概率给高分
                score = random.randint(40, PEER_REVIEW_MAX_SCORE)
            else:  # 60%概率给中等分数
                score = random.randint(25, 40)
            
            # 30%概率添加评论
            comment = None
            if random.random() < 0.3:
                comments = [
                    "谱面设计很有趣！",
                    "难度适中，很好玩",
                    "节奏感很棒",
                    "有些地方可以再优化一下",
                    "整体不错",
                    "创意很好！",
                    "这个段落很精彩"
                ]
                comment = random.choice(comments)
            
            # 10%概率标记为喜欢
            favorite = random.random() < 0.1
            
            try:
                PeerReviewService.submit_peer_review(
                    allocation_id=allocation.id,
                    score=score,
                    comment=comment,
                    favorite=favorite
                )
                submitted_count += 1
                
                if submitted_count % 10 == 0:  # 每10个显示一次进度
                    print(f"  已完成评分: {submitted_count}/{total_count}")
            
            except Exception as e:
                print(f"  ✗ 评分提交失败 ({allocation.reviewer.username} → {allocation.chart.song.title}): {e}")
        else:
            print(f"  - {allocation.reviewer.username} 跳过了对 {allocation.chart.song.title} 的评分")
    
    completion_rate = (submitted_count / total_count * 100) if total_count > 0 else 0
    print(f"\n✓ 评分模拟完成！")
    print(f"  - 已提交评分: {submitted_count}/{total_count} ({completion_rate:.1f}%)")
    print(f"  - 未完成评分: {total_count - submitted_count}\n")


def show_peer_review_stats(bidding_round):
    """显示评分统计信息"""
    print("=" * 60)
    print("评分统计信息")
    print("=" * 60 + "\n")
    
    # 获取所有谱面及其评分
    charts = Chart.objects.filter(bidding_round=bidding_round).select_related('user', 'song')
    
    print("【谱面评分情况】")
    print("-" * 60)
    for chart in charts:
        reviews = PeerReview.objects.filter(chart=chart)
        review_count = reviews.count()
        
        if review_count > 0:
            from django.db.models import Avg, Sum
            avg_score = reviews.aggregate(avg=Avg('score'))['avg']
            total_score = reviews.aggregate(total=Sum('score'))['total']
            favorite_count = reviews.filter(favorite=True).count()
            
            print(f"  {chart.user.username} - {chart.song.title}")
            print(f"    评分数: {review_count} | 平均分: {avg_score:.1f}/{PEER_REVIEW_MAX_SCORE} | 喜欢: {favorite_count}")
        else:
            print(f"  {chart.user.username} - {chart.song.title}")
            print(f"    评分数: 0 | 平均分: 暂无")
    
    print("\n【评分者完成情况】")
    print("-" * 60)
    test_users = User.objects.filter(username__startswith='bidtest_')
    for user in test_users:
        allocations = PeerReviewAllocation.objects.filter(reviewer=user, bidding_round=bidding_round)
        total_tasks = allocations.count()
        completed_tasks = allocations.filter(status='completed').count()
        
        if total_tasks > 0:
            completion_rate = (completed_tasks / total_tasks * 100)
            print(f"  {user.username}: {completed_tasks}/{total_tasks} ({completion_rate:.1f}%)")
        else:
            print(f"  {user.username}: 无评分任务")
    
    # 整体统计
    total_allocations = PeerReviewAllocation.objects.filter(bidding_round=bidding_round).count()
    completed_allocations = PeerReviewAllocation.objects.filter(
        bidding_round=bidding_round, 
        status='completed'
    ).count()
    total_reviews = PeerReview.objects.filter(chart__bidding_round=bidding_round).count()
    
    print("\n【整体统计】")
    print("-" * 60)
    print(f"  总分配任务: {total_allocations}")
    print(f"  已完成任务: {completed_allocations}")
    print(f"  实际评分数: {total_reviews}")
    print(f"  任务完成率: {(completed_allocations/total_allocations*100):.1f}%" if total_allocations > 0 else "  任务完成率: 0%")
    print(f"  参与谱面数: {charts.count()}")
    
    print("\n" + "=" * 60 + "\n")


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


def ask_user_continue(prompt, default="y"):
    """询问用户是否继续"""
    while True:
        try:
            response = input(f"\n{prompt} [{'Y/n' if default == 'y' else 'y/N'}]: ").strip().lower()
            if not response:
                response = default
            if response in ['y', 'yes', '是']:
                return True
            elif response in ['n', 'no', '否']:
                return False
            else:
                print("请输入 y/yes/是 或 n/no/否")
        except KeyboardInterrupt:
            print("\n\n用户中断操作")
            return False
        except EOFError:
            return default == 'y'


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("竞标分配与评分任务测试脚本 (分步骤执行)")
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
    
    # 步骤6: 执行竞标分配
    success = run_allocation(bidding_round)
    
    if not success:
        print("竞标分配失败，请检查错误信息")
        return
    
    # 步骤7: 显示竞标分配结果
    show_results(bidding_round)
    
    # 步骤8: 创建测试谱面
    charts = create_test_charts(users, songs, bidding_round)
    
    if not charts:
        print("未创建任何谱面，无法进行评分测试")
        print_basic_completion_info(bidding_round)
        return
    
    print("=" * 60)
    print("阶段一完成：竞标→制谱 流程已完成")
    print("=" * 60)
    print(f"✓ 已创建 {len(charts)} 个完成稿谱面")
    print(f"✓ 竞标轮次ID: {bidding_round.id}")
    print("✓ 所有谱面状态为'已提交'，可以进行评分")
    
    # 询问是否继续进行评分测试
    if not ask_user_continue("是否继续执行评分分配和提交测试？"):
        print("\n跳过评分测试，仅完成竞标和制谱阶段。")
        print_basic_completion_info(bidding_round)
        return
    
    print("\n继续执行评分测试...\n")
    
    # 步骤9: 执行评分任务分配
    peer_review_success = run_peer_review_allocation(bidding_round)
    
    if not peer_review_success:
        print("评分任务分配失败，评分测试结束")
        print_basic_completion_info(bidding_round)
        return
    
    # 询问是否模拟用户评分提交
    if not ask_user_continue("是否模拟用户提交评分？", default="y"):
        print("\n跳过评分提交模拟。")
        print("当前状态：评分任务已分配，等待用户提交评分。")
        print_evaluation_info(bidding_round)
        return
    
    # 步骤10: 模拟用户提交评分
    simulate_peer_reviews(bidding_round)
    
    # 步骤11: 显示评分统计结果
    show_peer_review_stats(bidding_round)
    
    print("完整测试流程结束！")
    print_full_completion_info(bidding_round)


def print_basic_completion_info(bidding_round):
    """打印基础完成信息（仅竞标和制谱）"""
    print("\n" + "=" * 60)
    print("测试完成信息")
    print("=" * 60)
    print("完成阶段：竞标分配 + 谱面创建")
    print(f"竞标轮次ID: {bidding_round.id}")
    print("测试用户: bidtest_1 ~ bidtest_10 (密码: test123)")
    print("可通过 Django Admin 查看详细数据")
    print("重新运行脚本会清除并重新生成所有数据")


def print_evaluation_info(bidding_round):
    """打印评分阶段信息"""
    print("\n" + "=" * 60)
    print("测试完成信息")
    print("=" * 60)
    print("完成阶段：竞标分配 + 谱面创建 + 评分任务分配")
    print(f"竞标轮次ID: {bidding_round.id}")
    print("测试用户: bidtest_1 ~ bidtest_10 (密码: test123)")
    print("评分任务已分配，可通过API或Admin手动提交评分")
    print("重新运行脚本会清除并重新生成所有数据")


def print_full_completion_info(bidding_round):
    """打印完整测试完成信息"""
    print("\n" + "=" * 60)
    print("完整测试完成信息")
    print("=" * 60)
    print("完成阶段：竞标分配 + 谱面创建 + 评分分配 + 评分模拟")
    print(f"竞标轮次ID: {bidding_round.id}")
    print("测试用户: bidtest_1 ~ bidtest_10 (密码: test123)")
    print("可通过 Django Admin 查看所有详细数据")
    print("重新运行脚本会清除并重新生成所有数据")
    print("\n测试覆盖范围：")
    print("  ✓ 竞标分配逻辑（同价随机、价高者得、保底分配）")
    print("  ✓ 谱面创建和状态管理")
    print("  ✓ 评分任务自动分配算法")
    print("  ✓ 用户评分提交模拟")
    print("  ✓ 评分统计和完成率计算")


if __name__ == '__main__':
    main()
