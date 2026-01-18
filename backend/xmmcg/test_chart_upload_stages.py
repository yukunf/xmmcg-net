"""
生成测试数据并验证第一、第二阶段谱面上传检测
"""

import os
import django
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.contrib.auth import get_user_model
from songs.models import Song, BidResult, Chart, BiddingRound
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def create_test_data():
    """创建测试数据"""
    print("=== 创建测试数据 ===\n")
    
    # 1. 创建测试用户
    username = f"test_upload_{timezone.now().timestamp()}"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': f'{username}@test.com'}
    )
    if created:
        user.set_password('test123')
        user.save()
        print(f"✓ 创建测试用户: {user.username}")
    else:
        print(f"✓ 使用现有用户: {user.username}")
    
    # 2. 创建测试歌曲
    audio_content = b'fake audio content for testing'
    audio_file = SimpleUploadedFile("test_song.mp3", audio_content, content_type="audio/mpeg")
    
    import hashlib
    audio_hash = hashlib.sha256(audio_content).hexdigest()
    
    song = Song.objects.create(
        title=f"TestSong_{int(timezone.now().timestamp())}",
        user=user,
        audio_file=audio_file,
        audio_hash=audio_hash,
        file_size=len(audio_content)
    )
    print(f"✓ 创建测试歌曲: {song.title} (ID: {song.id})\n")
    
    # 3. 创建第一阶段竞标轮次（歌曲竞标）
    round1 = BiddingRound.objects.create(
        name="Stage1TestRound",
        bidding_type='song',
        status='completed',
        started_at=timezone.now() - timedelta(days=2),
        completed_at=timezone.now() - timedelta(days=1)
    )
    print(f"✓ 创建第一阶段竞标轮次: {round1.name} (ID: {round1.id})")
    
    # 4. 创建第一阶段中标结果
    bid_result_stage1 = BidResult.objects.create(
        bidding_round=round1,
        user=user,
        song=song,
        bid_type='song',
        bid_amount=100
    )
    print(f"✓ 创建第一阶段中标结果 (ID: {bid_result_stage1.id})")
    print(f"  - 用户: {user.username}")
    print(f"  - 歌曲: {song.title}")
    print(f"  - 类型: {bid_result_stage1.bid_type}\n")
    
    # 5. 模拟提交第一阶段半成品谱面
    chart_content = '&des=TestDesigner\n&title=TestChart\n[0]E,2,,,'.encode('utf-8')
    chart_file = SimpleUploadedFile("maidata.txt", chart_content, content_type="text/plain")
    cover_content = b'fake image content'
    cover_file = SimpleUploadedFile("cover.jpg", cover_content, content_type="image/jpeg")
    
    chart_stage1 = Chart.objects.create(
        bidding_round=round1,
        user=user,
        song=song,
        bid_result=bid_result_stage1,
        status='part_submitted',
        designer='测试谱师',
        audio_file=audio_file,
        cover_image=cover_file,
        chart_file=chart_file,
        submitted_at=timezone.now(),
        is_part_one=True
    )
    print(f"✓ 创建第一阶段半成品谱面 (ID: {chart_stage1.id})")
    print(f"  - 谱师: {chart_stage1.designer}")
    print(f"  - 状态: {chart_stage1.status}")
    print(f"  - is_part_one: {chart_stage1.is_part_one}\n")
    
    # 6. 创建第二阶段竞标轮次（谱面竞标）
    round2 = BiddingRound.objects.create(
        name="Stage2TestRound",
        bidding_type='chart',
        status='active',
        started_at=timezone.now() - timedelta(days=1)
    )
    print(f"✓ 创建第二阶段竞标轮次: {round2.name} (ID: {round2.id})")
    
    # 7. 创建第二阶段中标结果（竞标第一阶段的半成品谱面）
    bid_result_stage2 = BidResult.objects.create(
        bidding_round=round2,
        user=user,
        chart=chart_stage1,  # 指向第一阶段的半成品
        bid_type='chart',
        bid_amount=50
    )
    print(f"✓ 创建第二阶段中标结果 (ID: {bid_result_stage2.id})")
    print(f"  - 用户: {user.username}")
    print(f"  - 谱面: {chart_stage1.song.title}")
    print(f"  - 类型: {bid_result_stage2.bid_type}\n")
    
    return user, song, bid_result_stage1, bid_result_stage2, chart_stage1


def test_upload_detection():
    """测试上传检测逻辑"""
    print("\n" + "="*60)
    print("=== 测试谱面上传检测逻辑 ===")
    print("="*60 + "\n")
    
    # 创建测试数据
    user, song, bid_result1, bid_result2, chart1 = create_test_data()
    
    print("\n" + "="*60)
    print("=== 第一阶段检测 ===")
    print("="*60 + "\n")
    
    # 测试1: 检查第一阶段是否已有谱面
    existing_stage1 = Chart.objects.filter(
        user=user,
        song=song,
        bidding_round=bid_result1.bidding_round,
        is_part_one=True
    ).first()
    
    if existing_stage1:
        print("✓ 第一阶段检测结果:")
        print(f"  - 状态: 已提交半成品")
        print(f"  - 谱面ID: {existing_stage1.id}")
        print(f"  - 预期行为: ❌ 应拒绝再次上传第一阶段谱面")
        print(f"  - 前端显示: '您已提交第一阶段半成品，请等待第二阶段竞标'")
    else:
        print("✗ 第一阶段检测结果:")
        print(f"  - 状态: 未提交")
        print(f"  - 预期行为: ✅ 允许上传第一阶段谱面")
    
    print("\n" + "="*60)
    print("=== 第二阶段检测 ===")
    print("="*60 + "\n")
    
    # 测试2: 检查第二阶段是否已有完成稿
    song_target = bid_result2.chart.song if bid_result2.chart else None
    existing_stage2 = Chart.objects.filter(
        user=user,
        bidding_round=bid_result2.bidding_round,
        song=song_target,
        is_part_one=False,
        completion_bid_result=bid_result2
    ).first()
    
    if existing_stage2:
        print("✓ 第二阶段检测结果:")
        print(f"  - 状态: 已提交完成稿")
        print(f"  - 谱面ID: {existing_stage2.id}")
        print(f"  - 预期行为: ❌ 应拒绝再次上传第二阶段谱面")
        print(f"  - 前端显示: '您已提交第二阶段完成稿，无法再次上传'")
    else:
        print("✓ 第二阶段检测结果:")
        print(f"  - 状态: 未提交完成稿")
        print(f"  - 预期行为: ✅ 允许上传第二阶段谱面")
        print(f"  - 前端显示: 显示上传表单，允许提交完成稿")
    
    # 模拟提交第二阶段完成稿
    print("\n" + "-"*60)
    print("模拟提交第二阶段完成稿...")
    print("-"*60 + "\n")
    
    chart_content2 = '&des=TestDesignerFinal\n&title=TestChartFinal\n[0]E,2,,,\n[1]A,4,,,'.encode('utf-8')
    chart_file2 = SimpleUploadedFile("maidata_final.txt", chart_content2, content_type="text/plain")
    audio_file2 = SimpleUploadedFile("test_song2.mp3", b'fake audio', content_type="audio/mpeg")
    cover_file2 = SimpleUploadedFile("cover2.jpg", b'fake image', content_type="image/jpeg")
    
    chart_stage2 = Chart.objects.create(
        bidding_round=bid_result2.bidding_round,
        user=user,
        song=song_target,
        status='final_submitted',
        designer='测试谱师完成版',
        audio_file=audio_file2,
        cover_image=cover_file2,
        chart_file=chart_file2,
        submitted_at=timezone.now(),
        is_part_one=False,
        part_one_chart=chart1,
        completion_bid_result=bid_result2
    )
    
    print(f"✓ 创建第二阶段完成稿 (ID: {chart_stage2.id})")
    print(f"  - 谱师: {chart_stage2.designer}")
    print(f"  - 状态: {chart_stage2.status}")
    print(f"  - is_part_one: {chart_stage2.is_part_one}")
    print(f"  - part_one_chart: {chart_stage2.part_one_chart.id if chart_stage2.part_one_chart else None}")
    
    # 再次检测第二阶段
    print("\n" + "="*60)
    print("=== 第二阶段再次检测（已提交后） ===")
    print("="*60 + "\n")
    
    existing_stage2_after = Chart.objects.filter(
        user=user,
        bidding_round=bid_result2.bidding_round,
        song=song_target,
        is_part_one=False,
        completion_bid_result=bid_result2
    ).first()
    
    if existing_stage2_after:
        print("✓ 第二阶段检测结果:")
        print(f"  - 状态: 已提交完成稿")
        print(f"  - 谱面ID: {existing_stage2_after.id}")
        print(f"  - 预期行为: ❌ 应拒绝再次上传第二阶段谱面")
        print(f"  - 前端显示: '您已提交第二阶段完成稿，无法再次上传'")
        print(f"  - 上传按钮: 禁用，显示'已提交'")
    
    # 总结
    print("\n" + "="*60)
    print("=== 测试总结 ===")
    print("="*60 + "\n")
    
    all_charts = Chart.objects.filter(user=user).order_by('created_at')
    print(f"用户 {user.username} 的所有谱面 ({all_charts.count()} 个):\n")
    
    for idx, chart in enumerate(all_charts, 1):
        print(f"{idx}. 谱面 ID: {chart.id}")
        print(f"   - 歌曲: {chart.song.title}")
        print(f"   - 谱师: {chart.designer}")
        print(f"   - 阶段: {'第一阶段（半成品）' if chart.is_part_one else '第二阶段（完成稿）'}")
        print(f"   - 状态: {chart.status}")
        print(f"   - 轮次: {chart.bidding_round.name}")
        print(f"   - 提交时间: {chart.submitted_at}")
        if not chart.is_part_one and chart.part_one_chart:
            print(f"   - 基于谱面: ID {chart.part_one_chart.id}")
        print()
    
    print("="*60)
    print("测试完成！")
    print("="*60)
    print("\n前端测试要点:")
    print("1. 登录用户:", user.username)
    print("2. 第一阶段中标结果ID:", bid_result1.id, "（已提交，应阻止上传）")
    print("3. 第二阶段中标结果ID:", bid_result2.id, "（已提交，应阻止上传）")
    print("\n后端API测试:")
    print(f"POST /api/songs/charts/{bid_result1.id}/submit/ - 应返回400错误")
    print(f"POST /api/songs/charts/{bid_result2.id}/submit/ - 应返回400错误")


if __name__ == '__main__':
    test_upload_detection()
