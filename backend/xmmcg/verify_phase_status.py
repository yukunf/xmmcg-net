#!/usr/bin/env python
"""验证阶段状态和前端访问权限"""

import os
import sys
import django
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from songs.models import CompetitionPhase

CST = ZoneInfo('Asia/Shanghai')

def verify_phases():
    """验证阶段状态"""
    
    now = datetime.now(CST)
    
    print("=" * 70)
    print(f"📅 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 70)
    print()
    
    phases = CompetitionPhase.objects.all().order_by('order', 'start_time')
    
    print("📊 阶段状态总览:\n")
    print(f"{'阶段名称':<15} {'phase_key':<20} {'实时状态':<10} {'is_active':<10} {'前端行为'}")
    print("-" * 70)
    
    for phase in phases:
        status = phase.status
        status_emoji = {
            'upcoming': '⏳ 未开始',
            'active': '✅ 进行中',
            'ended': '🔴 已结束'
        }
        
        # 判断前端行为
        frontend_behavior = ""
        if phase.phase_key == 'music_bid':
            if status == 'active' and phase.is_active:
                frontend_behavior = "✅ 显示竞标按钮"
            else:
                frontend_behavior = "❌ 隐藏竞标按钮"
        elif phase.phase_key == 'chart_bid':
            if status == 'active' and phase.is_active:
                frontend_behavior = "✅ 显示竞标按钮"
            else:
                frontend_behavior = "❌ 隐藏竞标按钮"
        elif phase.phase_key == 'music_submit':
            if status == 'active' and phase.is_active:
                frontend_behavior = "✅ 允许上传歌曲"
            else:
                frontend_behavior = "❌ 禁止上传歌曲"
        elif phase.phase_key in ['mapping1', 'mapping2']:
            if status == 'active' and phase.is_active:
                frontend_behavior = "✅ 允许上传谱面"
            else:
                frontend_behavior = "❌ 禁止上传谱面"
        
        print(f"{phase.name:<15} {phase.phase_key:<20} {status_emoji.get(status, '❓'):<12} {str(phase.is_active):<10} {frontend_behavior}")
    
    print()
    print("=" * 70)
    print("🔍 关键验证点:\n")
    
    # 验证歌曲竞标阶段
    song_bid = phases.filter(phase_key='music_bid').first()
    if song_bid:
        print(f"1️⃣  歌曲竞标阶段 (music_bid):")
        print(f"   - 实时状态: {song_bid.status}")
        print(f"   - is_active: {song_bid.is_active}")
        print(f"   - 结束时间: {song_bid.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if song_bid.status == 'active' and song_bid.is_active:
            print(f"   ✅ 前端应显示歌曲竞标按钮")
            print(f"   ⏰ 距离结束还有: {song_bid.get_time_remaining()}")
        else:
            print(f"   ❌ 前端应隐藏歌曲竞标按钮")
        print()
    
    # 验证谱面竞标阶段
    chart_bid = phases.filter(phase_key='chart_bid').first()
    if chart_bid:
        print(f"2️⃣  谱面竞标阶段 (chart_bid):")
        print(f"   - 实时状态: {chart_bid.status}")
        print(f"   - is_active: {chart_bid.is_active}")
        print(f"   - 开始时间: {chart_bid.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if chart_bid.status == 'active' and chart_bid.is_active:
            print(f"   ✅ 前端应显示谱面竞标按钮")
        else:
            print(f"   ❌ 前端应隐藏谱面竞标按钮")
            if chart_bid.status == 'upcoming':
                print(f"   ⏰ 距离开始还有: {chart_bid.get_time_remaining()}")
        print()
    
    # 验证已过期阶段
    music_submit = phases.filter(phase_key='music_submit').first()
    if music_submit:
        print(f"3️⃣  歌曲提交期 (music_submit) - 应已过期:")
        print(f"   - 实时状态: {music_submit.status}")
        print(f"   - is_active: {music_submit.is_active}")
        
        if music_submit.status == 'ended' and not music_submit.is_active:
            print(f"   ✅ 正确：已过期且已停用")
        elif music_submit.status == 'ended' and music_submit.is_active:
            print(f"   ⚠️  警告：已过期但仍处于激活状态！")
        print()
    
    print("=" * 70)
    print("\n🧪 前端测试步骤:\n")
    print("1. 打开前端开发服务器：cd front && npm run dev")
    print("2. 访问 Songs 页面：")
    print("   - 应能看到 '竞标' 按钮（因为 song_bid 正在进行）")
    print("   - 点击后应能正常提交竞标")
    print("3. 访问 Charts 页面：")
    print("   - 应看不到 '竞标' 按钮（因为 chart_bid 尚未开始）")
    print("4. 30分钟后再次测试：")
    print("   - 运行：python manage.py update_phase_status")
    print("   - song_bid 应被停用，竞标按钮应消失")
    print("\n" + "=" * 70)


if __name__ == '__main__':
    try:
        verify_phases()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
