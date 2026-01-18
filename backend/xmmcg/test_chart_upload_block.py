"""
测试谱面上传阻止功能
验证：
1. 第一阶段提交半成品后，无法再次上传
2. 第二阶段提交完成稿后，无法再次上传
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.contrib.auth import get_user_model
from songs.models import Song, BidResult, Chart, BiddingRound
from django.utils import timezone

User = get_user_model()

def test_chart_upload_blocking():
    print("=== 测试谱面上传阻止功能 ===\n")
    
    # 1. 查找测试用户和数据
    user = User.objects.first()
    if not user:
        print("❌ 没有找到测试用户")
        return
    
    print(f"✓ 使用测试用户: {user.username}\n")
    
    # 2. 查找第一阶段的中标结果（bid_type='song'）
    song_bid_result = BidResult.objects.filter(
        user=user,
        bid_type='song'
    ).first()
    
    if song_bid_result:
        print(f"✓ 找到第一阶段中标结果:")
        print(f"  - ID: {song_bid_result.id}")
        print(f"  - 歌曲: {song_bid_result.song.title}")
        print(f"  - 类型: {song_bid_result.bid_type}")
        
        # 检查是否已有谱面
        existing_chart = Chart.objects.filter(
            user=user,
            song=song_bid_result.song,
            bidding_round=song_bid_result.bidding_round,
            is_part_one=True
        ).first()
        
        if existing_chart:
            print(f"  - ✓ 已提交第一阶段谱面 (ID: {existing_chart.id})")
            print(f"  - 谱师: {existing_chart.designer}")
            print(f"  - 状态: {existing_chart.status}")
            print(f"  - 预期行为: 后端应拒绝再次上传\n")
        else:
            print(f"  - ✗ 尚未提交第一阶段谱面")
            print(f"  - 预期行为: 允许上传\n")
    else:
        print("✗ 没有找到第一阶段中标结果\n")
    
    # 3. 查找第二阶段的中标结果（bid_type='chart'）
    chart_bid_result = BidResult.objects.filter(
        user=user,
        bid_type='chart'
    ).first()
    
    if chart_bid_result:
        print(f"✓ 找到第二阶段中标结果:")
        print(f"  - ID: {chart_bid_result.id}")
        print(f"  - 谱面: {chart_bid_result.chart.song.title if chart_bid_result.chart else 'N/A'}")
        print(f"  - 类型: {chart_bid_result.bid_type}")
        
        # 检查是否已有完成稿
        if chart_bid_result.chart:
            song_target = chart_bid_result.chart.song
            existing_completion = Chart.objects.filter(
                user=user,
                bidding_round=chart_bid_result.bidding_round,
                song=song_target,
                is_part_one=False,
                completion_bid_result=chart_bid_result
            ).first()
            
            if existing_completion:
                print(f"  - ✓ 已提交第二阶段完成稿 (ID: {existing_completion.id})")
                print(f"  - 谱师: {existing_completion.designer}")
                print(f"  - 状态: {existing_completion.status}")
                print(f"  - 预期行为: 后端应拒绝再次上传\n")
            else:
                print(f"  - ✗ 尚未提交第二阶段完成稿")
                print(f"  - 预期行为: 允许上传\n")
        else:
            print(f"  - ✗ 中标结果没有关联谱面\n")
    else:
        print("✗ 没有找到第二阶段中标结果\n")
    
    # 4. 显示所有谱面状态
    all_charts = Chart.objects.filter(user=user).order_by('-created_at')
    print(f"=== 用户所有谱面 ({all_charts.count()} 个) ===")
    for chart in all_charts:
        print(f"\n谱面 ID: {chart.id}")
        print(f"  - 歌曲: {chart.song.title}")
        print(f"  - 谱师: {chart.designer}")
        print(f"  - 状态: {chart.status}")
        print(f"  - 是第一部分: {chart.is_part_one}")
        print(f"  - 轮次: {chart.bidding_round.name if chart.bidding_round else 'N/A'}")
        print(f"  - 提交时间: {chart.submitted_at}")

if __name__ == '__main__':
    test_chart_upload_blocking()
