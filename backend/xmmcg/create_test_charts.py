"""
生成谱面测试数据脚本
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.contrib.auth.models import User
from songs.models import Song, BiddingRound, BidResult, Chart, CompetitionPhase
from django.core.files.base import ContentFile
from django.utils import timezone
import random

def create_test_charts():
    """创建测试谱面数据"""
    
    # 获取或创建测试用户
    user1, _ = User.objects.get_or_create(username='testuser1', defaults={'email': 'test1@example.com'})
    user2, _ = User.objects.get_or_create(username='testuser2', defaults={'email': 'test2@example.com'})
    user3, _ = User.objects.get_or_create(username='testuser3', defaults={'email': 'test3@example.com'})
    
    users = [user1, user2, user3]
    
    # 获取或创建竞标轮次
    round_obj, _ = BiddingRound.objects.get_or_create(
        name='测试竞标轮次',
        defaults={
            'status': 'completed',
            'bidding_type': 'song'
        }
    )
    
    # 创建测试歌曲
    songs_data = [
        {'title': '夜的第七章', 'designer': 'Jay Chou'},
        {'title': '告白气球', 'designer': '周杰伦'},
        {'title': '稻香', 'designer': 'J.Chou'},
        {'title': '青花瓷', 'designer': 'JayChou'},
        {'title': '七里香', 'designer': 'Zhou JL'},
    ]
    
    print('开始创建测试数据...')
    
    for idx, song_data in enumerate(songs_data):
        user = users[idx % len(users)]
        
        # 创建歌曲
        song, created = Song.objects.get_or_create(
            title=song_data['title'],
            user=user,
            defaults={
                'audio_hash': f'test_hash_{idx}',
                'file_size': 1024000
            }
        )
        
        if created:
            # 创建假的音频文件
            song.audio_file.save(
                f'test_audio_{idx}.mp3',
                ContentFile(b'fake audio content'),
                save=True
            )
            print(f'✓ 创建歌曲: {song.title}')
        else:
            print(f'○ 歌曲已存在: {song.title}')
        
        # 创建竞标结果
        bid_result, created = BidResult.objects.get_or_create(
            bidding_round=round_obj,
            user=user,
            song=song,
            defaults={
                'bid_type': 'song',
                'bid_amount': random.randint(100, 500),
                'allocation_type': 'win'
            }
        )
        
        if created:
            print(f'  ✓ 创建竞标结果')
        
        # 创建谱面
        chart, created = Chart.objects.get_or_create(
            bidding_round=round_obj,
            user=user,
            song=song,
            defaults={
                'bid_result': bid_result,
                'designer': song_data['designer'],
                'status': random.choice(['part_submitted', 'final_submitted', 'under_review', 'reviewed']),
                'review_count': random.randint(0, 10),
                'total_score': 0,
                'average_score': 0.0,
                'submitted_at': timezone.now()
            }
        )
        
        if created:
            # 创建测试文件
            maidata_content = f"""&title={song.title}
&artist=Test Artist
&des={song_data['designer']}
&first=100
&lv_1=5
&lv_2=7
&lv_3=9
&lv_4=11

// 测试谱面内容
1---2---,
3---4---,
"""
            chart.chart_file.save(
                'maidata.txt',
                ContentFile(maidata_content.encode('utf-8')),
                save=False
            )
            
            # 创建假音频和封面
            chart.audio_file.save(
                f'chart_audio_{idx}.mp3',
                ContentFile(b'fake chart audio'),
                save=False
            )
            
            # 计算平均分
            if chart.review_count > 0:
                chart.total_score = chart.review_count * random.randint(30, 50)
                chart.average_score = round(chart.total_score / chart.review_count, 2)
            
            chart.save()
            print(f'  ✓ 创建谱面: {chart.designer} - 状态: {chart.get_status_display()}')
        else:
            print(f'  ○ 谱面已存在: {chart.designer}')
    
    print('\n测试数据创建完成！')
    print(f'总计创建: {Chart.objects.count()} 个谱面')


if __name__ == '__main__':
    create_test_charts()
