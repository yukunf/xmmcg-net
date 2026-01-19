"""
完整的谱面上传流程示例
展示如何使用 MajdataService 上传半成品谱面
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from songs.majdata_service import MajdataService


def example_upload_part_chart():
    """示例：上传半成品谱面"""
    
    print("=" * 70)
    print("半成品谱面上传示例")
    print("=" * 70)
    
    # 准备 maidata.txt 内容
    maidata_content = """&title=14平米にスーベニア
&artist=ChouCho
&des=测试谱师
&lv_1=1
&lv_2=3
&lv_3=5
&lv_4=7

# Basic
(120)
{4}
1,
2,
3,
4,
"""
    
    print("\n📄 原始 maidata.txt 内容:")
    print("-" * 70)
    print(maidata_content[:200])
    print("...")
    
    # 模拟修改（半成品）
    modified_content = MajdataService._modify_maidata_for_part_chart(maidata_content)
    
    print("\n📝 修改后的 maidata.txt 内容（半成品）:")
    print("-" * 70)
    print(modified_content[:200])
    print("...")
    
    # 检查修改是否正确
    if '&title=[谱面碎片]14平米にスーベニア' in modified_content:
        print("\n✅ 标题修改成功！")
    else:
        print("\n❌ 标题修改失败！")
        return
    
    print("\n" + "=" * 70)
    print("上传准备")
    print("=" * 70)
    
    # 准备上传数据结构
    upload_data = {
        'maidata_content': maidata_content,  # 原始内容（会自动修改）
        'audio_file': None,  # 实际使用时传入文件对象
        'cover_file': None,  # 实际使用时传入文件对象
        'video_file': None,  # 可选
        'is_part_chart': True,  # 标记为半成品
        'folder_name': '14平米にスーベニア_测试用户'
    }
    
    print("\n📦 上传数据结构:")
    print(f"  - maidata_content: {len(maidata_content)} 字符")
    print(f"  - is_part_chart: {upload_data['is_part_chart']}")
    print(f"  - folder_name: {upload_data['folder_name']}")
    print(f"  - audio_file: {'<文件对象>' if upload_data['audio_file'] else '未提供（仅演示）'}")
    print(f"  - cover_file: {'<文件对象>' if upload_data['cover_file'] else '未提供（仅演示）'}")
    print(f"  - video_file: {'<文件对象>' if upload_data['video_file'] else '未提供（可选）'}")
    
    print("\n" + "=" * 70)
    print("预期上传流程")
    print("=" * 70)
    print("""
1. 调用 MajdataService.upload_chart(upload_data)
2. 检测到 is_part_chart=True
3. 自动调用 _modify_maidata_for_part_chart()
4. maidata.txt 标题变为: &title=[谱面碎片]14平米にスーベニア
5. 按顺序准备上传文件：
   - formfiles: maidata.txt
   - formfiles: bg.png/bg.jpg (封面)
   - formfiles: track.mp3 (音频)
   - formfiles: bg.mp4/pv.mp4 (视频，可选)
6. POST 到 {MAJDATA_UPLOAD_URL}
7. 返回上传结果
    """)
    
    print("\n" + "=" * 70)
    print("注意事项")
    print("=" * 70)
    print("""
⚠️ 实际上传需要：
1. 配置正确的 MAJDATA_USERNAME 和 MAJDATA_PASSWD_HASHED
2. 提供有效的音频文件和封面文件
3. 确保网络连接到 Majdata.net

💡 当前仅演示标题修改功能，完整上传请参考：
   - MAJDATA_INTEGRATION.md
   - songs/views.py 第1109行（已集成的上传代码）
    """)
    
    print("\n" + "=" * 70)
    print("示例完成！")
    print("=" * 70)


def example_upload_complete_chart():
    """示例：上传完整谱面（不修改标题）"""
    
    print("\n\n" + "=" * 70)
    print("完整谱面上传示例")
    print("=" * 70)
    
    maidata_content = """&title=夏日海风
&artist=原创歌手
&des=专业谱师
&lv_4=10+

# Master
(180)
{16}
1-2-3-4[16:1],
"""
    
    print("\n📄 maidata.txt 内容:")
    print("-" * 70)
    print(maidata_content)
    
    # 完整谱面不修改标题
    modified_content = maidata_content  # is_part_chart=False 时不调用修改函数
    
    print("\n✅ 完整谱面上传时标题保持不变")
    print(f"   标题: &title=夏日海风")
    
    upload_data = {
        'maidata_content': maidata_content,
        'is_part_chart': False,  # 完整谱面
        'folder_name': '夏日海风_专业谱师'
    }
    
    print(f"\n📦 is_part_chart: {upload_data['is_part_chart']} → 不修改标题")


if __name__ == '__main__':
    # 演示半成品谱面上传
    example_upload_part_chart()
    
    # 演示完整谱面上传
    example_upload_complete_chart()
