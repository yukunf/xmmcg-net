#!/usr/bin/env python
"""
示例：向数据库添加带背景图片的Banner
"""

import os
import sys
import django

# 配置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
sys.path.insert(0, r'd:\code\xmmcg\backend\xmmcg')
django.setup()

from songs.models import Banner

# 示例1：添加带服务器本地图片的Banner
banner1 = Banner.objects.create(
    title='XMMCG 2024 竞赛',
    content='参与音游谱面制作竞赛，展示你的创作才华！',
    image_url='http://localhost:8000/media/banners/competition-bg.jpg',  # 服务器图片URL
    link='/songs',
    button_text='立即参与',
    color='#409EFF',
    priority=10,
    is_active=True
)

# 示例2：添加带外部图片的Banner  
banner2 = Banner.objects.create(
    title='新手教程',
    content='学习如何创作高质量的音游谱面',
    image_url='https://your-domain.com/static/images/tutorial-bg.png',  # 外部图片URL
    link='/tutorial',
    button_text='开始学习', 
    color='#67C23A',
    priority=8,
    is_active=True
)

# 示例3：使用相对路径（推荐用于服务器内部图片）
banner3 = Banner.objects.create(
    title='最新资讯',
    content='了解竞赛最新动态和规则变更',
    image_url='/media/banners/news-bg.jpg',  # 相对路径
    link='/announcements',
    button_text='查看详情',
    color='#E6A23C', 
    priority=5,
    is_active=True
)

print(f"✅ 成功创建了 3 个带背景图片的Banner")
print(f"Banner 1 ID: {banner1.id} - {banner1.title}")
print(f"Banner 2 ID: {banner2.id} - {banner2.title}")  
print(f"Banner 3 ID: {banner3.id} - {banner3.title}")