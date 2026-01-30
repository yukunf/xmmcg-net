#!/usr/bin/env python
"""创建测试阶段数据，用于验证竞标系统的阶段检查功能"""

import os
import sys
import django
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# 配置 Django 环境
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from songs.models import CompetitionPhase

# 使用 Asia/Shanghai 时区
CST = ZoneInfo('Asia/Shanghai')

def create_test_phases():
    """创建测试阶段数据"""
    
    now = datetime.now(CST)
    
    # 清理旧的测试数据（可选）
    print("=" * 60)
    print("🗑️  清理旧测试阶段...")
    deleted_count = CompetitionPhase.objects.filter(
        phase_key__in=['music_submit', 'music_bid', 'music_allocation', 'mapping1', 'chart_bid', 'mapping2', 'eval']
    ).delete()[0]
    print(f"已删除 {deleted_count} 个旧阶段\n")
    
    # 创建测试阶段
    test_phases = [
        {
            'name': '歌曲提交期',
            'phase_key': 'music_submit',
            'description': '音乐人上传原创歌曲',
            'submissions_type': 'songs',
            'start_time': now - timedelta(hours=2),  # 2小时前开始
            'end_time': now - timedelta(hours=1),    # 1小时前结束（已过期）
            'order': 10,
            'is_active': True,  # 初始设为 True，等待 update_phase_status 更新
            'page_access': {'songs': True, 'charts': False}
        },
        {
            'name': '歌曲竞标期',
            'phase_key': 'music_bid',
            'description': '谱师对歌曲进行竞标',
            'submissions_type': 'songs',
            'start_time': now - timedelta(minutes=30),  # 30分钟前开始
            'end_time': now + timedelta(minutes=30),    # 30分钟后结束（进行中）
            'order': 20,
            'is_active': True,
            'page_access': {'songs': True, 'charts': False}
        },
        {
            'name': '歌曲分配期（仅视觉）',
            'phase_key': 'music_allocation',
            'description': '系统自动分配歌曲给谱师',
            'submissions_type': 'songs',
            'start_time': now + timedelta(minutes=35),  # 竞标结束5分钟后
            'end_time': now + timedelta(minutes=55),    # 20分钟分配期
            'order': 25,
            'is_active': True,
            'page_access': {'songs': True, 'charts': False}
        },
        {
            'name': '第一次谱面制作期',
            'phase_key': 'mapping1',
            'description': '谱师制作并提交第一阶段谱面',
            'submissions_type': 'charts',
            'start_time': now + timedelta(hours=1),   # 1小时后开始（未开始）
            'end_time': now + timedelta(hours=3),     # 3小时后结束
            'order': 30,
            'is_active': True,
            'page_access': {'songs': False, 'charts': True}
        },
        {
            'name': '谱面竞标期',
            'phase_key': 'chart_bid',
            'description': '选手对谱面进行竞标',
            'submissions_type': 'charts',
            'start_time': now + timedelta(hours=4),   # 4小时后开始（未开始）
            'end_time': now + timedelta(hours=6),     # 6小时后结束
            'order': 40,
            'is_active': True,
            'page_access': {'songs': False, 'charts': True}
        },
        {
            'name': '第二次谱面制作期',
            'phase_key': 'mapping2',
            'description': '中标选手完成最终谱面',
            'submissions_type': 'charts',
            'start_time': now + timedelta(hours=7),   # 7小时后开始（未开始）
            'end_time': now + timedelta(hours=9),     # 9小时后结束
            'order': 50,
            'is_active': True,
            'page_access': {'songs': False, 'charts': True}
        },
        {
            'name': '互评期',
            'phase_key': 'eval',
            'description': '选手互相评价作品',
            'submissions_type': 'charts',
            'start_time': now + timedelta(hours=10),  # 10小时后开始（未开始）
            'end_time': now + timedelta(hours=13),    # 13小时后结束
            'order': 60,
            'is_active': True,
            'page_access': {'songs': False, 'charts': False, 'eval': True}
        },
    ]
    
    print("=" * 60)
    print("📝 创建测试阶段...\n")
    
    created_phases = []
    for data in test_phases:
        phase = CompetitionPhase.objects.create(**data)
        created_phases.append(phase)
        
        status = phase.status  # 使用属性而不是方法
        status_emoji = {
            'upcoming': '⏳',
            'active': '✅',
            'ended': '🔴'
        }
        
        print(f"{status_emoji.get(status, '❓')} [{phase.phase_key}] {phase.name}")
        print(f"   开始: {phase.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   结束: {phase.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   状态: {status}")
        print(f"   is_active: {phase.is_active}")
        print()
    
    print("=" * 60)
    print("✅ 测试阶段创建完成！\n")
    
    # 显示当前时间
    print(f"📅 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n")
    
    # 显示测试说明
    print("=" * 60)
    print("🧪 测试指南:\n")
    print("1️⃣  运行 dry-run 测试:")
    print("   python manage.py update_phase_status --dry-run\n")
    print("   预期结果:")
    print("   - music_submit (已过期) → is_active 应改为 False")
    print("   - music_bid (进行中) → is_active 保持 True")
    print("   - music_allocation, mapping1, chart_bid, mapping2, eval (未开始) → is_active 应改为 False\n")
    
    print("2️⃣  运行实际更新:")
    print("   python manage.py update_phase_status\n")
    
    print("3️⃣  前端测试:")
    print("   - 打开 Songs 页面，应能看到 '竞标' 按钮（music_bid 阶段活跃）")
    print("   - 打开 Charts 页面，应看不到 '竞标' 按钮（chart_bid 未开始）")
    print("   - 30分钟后 music_bid 结束，竞标按钮应自动消失\n")
    
    print("4️⃣  测试定时任务:")
    print("   - 在 30 分钟内重复运行 update_phase_status")
    print("   - 观察 is_active 状态的变化\n")
    
    print("=" * 60)
    
    return created_phases


if __name__ == '__main__':
    try:
        phases = create_test_phases()
        print(f"\n✅ 成功创建 {len(phases)} 个测试阶段")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
