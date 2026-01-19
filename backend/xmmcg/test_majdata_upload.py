"""
测试 Majdata.net 上传功能
验证 MajdataService 的登录和上传流程
"""

import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from songs.majdata_service import MajdataService
from songs.models import Chart, BidResult, Song, User
from django.conf import settings
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


def create_test_maidata():
    """创建测试用的 maidata.txt 内容"""
    maidata_content = """&title=测试谱面
&artist=测试艺术家
&des=测试制作者
&lv_1=1
&lv_2=5
&lv_3=9
&lv_4=12
&lv_7=13+
&wholebpm=150

&first=0
&inote_1=
E1,
&inote_2=
E1,
E2,
&inote_3=
E1,
E2,
E3,
&inote_4=
E1,
E2,
E3,
E4,
&inote_7=
E1,
E2,
E3,
E4,
E5,
"""
    return maidata_content


def create_test_files():
    """创建测试文件"""
    # 创建 maidata.txt
    maidata_content = create_test_maidata()
    maidata_file = InMemoryUploadedFile(
        file=BytesIO(maidata_content.encode('utf-8')),
        field_name='maidata',
        name='maidata.txt',
        content_type='text/plain',
        size=len(maidata_content),
        charset='utf-8'
    )
    
    # 创建测试音频文件（空文件用于测试）
    audio_content = b'fake audio data for testing'
    audio_file = InMemoryUploadedFile(
        file=BytesIO(audio_content),
        field_name='track',
        name='track.mp3',
        content_type='audio/mpeg',
        size=len(audio_content),
        charset=None
    )
    
    # 创建测试背景图（空文件用于测试）
    bg_content = b'fake image data for testing'
    bg_file = InMemoryUploadedFile(
        file=BytesIO(bg_content),
        field_name='bg',
        name='bg.jpg',
        content_type='image/jpeg',
        size=len(bg_content),
        charset=None
    )
    
    return maidata_file, audio_file, bg_file


def test_login():
    """测试登录功能"""
    print("\n========== 测试 Majdata.net 登录 ==========")
    
    print(f"配置信息:")
    print(f"  LOGIN_URL: {settings.MAJDATA_LOGIN_URL}")
    print(f"  USERNAME: {settings.MAJDATA_USERNAME}")
    print(f"  PASSWORD: {settings.MAJDATA_PASSWD_HASHED}...")
    
    session = MajdataService.get_session()
    
    if session:
        print("✅ 登录成功")
        print(f"  Session cookies: {dict(session.cookies)}")
        return True
    else:
        print("❌ 登录失败")
        return False


def test_upload_full_chart():
    """测试完整谱面上传"""
    print("\n========== 测试完整谱面上传 ==========")
    
    # 创建测试数据
    user = User.objects.filter(username='test_user').first()
    if not user:
        user = User.objects.create_user(username='test_user', password='test123')
        print(f"✅ 创建测试用户: {user.username}")
    
    song = Song.objects.filter(title='测试歌曲').first()
    if not song:
        song = Song.objects.create(
            user=user,
            title='测试歌曲',
            artist='测试艺术家',
            audio_file='songs/test.mp3'
        )
        print(f"✅ 创建测试歌曲: {song.title}")
    
    # 创建 Chart 对象（完整谱面）
    chart = Chart.objects.filter(song=song, user=user).first()
    if not chart:
        chart = Chart.objects.create(
            song=song,
            user=user,
            status='pending',
            part_submitted=False  # 完整谱面
        )
        print(f"✅ 创建测试谱面: Chart #{chart.id}")
    
    # 准备上传文件
    maidata_file, audio_file, bg_file = create_test_files()
    
    print(f"\n开始上传...")
    print(f"  谱面ID: {chart.id}")
    print(f"  是否为碎片: {chart.part_submitted}")
    
    try:
        result = MajdataService.upload_chart(
            chart=chart,
            maidata_file=maidata_file,
            audio_file=audio_file,
            bg_file=bg_file
        )
        
        if result:
            print(f"✅ 上传成功!")
            print(f"  返回结果: {result}")
            
            # 验证 chart_url 是否已设置
            chart.refresh_from_db()
            if chart.chart_url:
                print(f"  谱面URL: {chart.chart_url}")
            return True
        else:
            print(f"❌ 上传失败")
            return False
            
    except Exception as e:
        print(f"❌ 上传异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_upload_part_chart():
    """测试碎片谱面上传（带标题修改）"""
    print("\n========== 测试碎片谱面上传 ==========")
    
    # 创建测试数据
    user = User.objects.filter(username='test_user').first()
    song = Song.objects.filter(title='测试歌曲').first()
    
    # 创建 Chart 对象（碎片谱面）
    part_chart = Chart.objects.create(
        song=song,
        user=user,
        status='pending',
        part_submitted=True  # 碎片谱面
    )
    print(f"✅ 创建碎片谱面: Chart #{part_chart.id}")
    
    # 准备上传文件
    maidata_file, audio_file, bg_file = create_test_files()
    
    print(f"\n开始上传...")
    print(f"  谱面ID: {part_chart.id}")
    print(f"  是否为碎片: {part_chart.part_submitted}")
    
    try:
        result = MajdataService.upload_chart(
            chart=part_chart,
            maidata_file=maidata_file,
            audio_file=audio_file,
            bg_file=bg_file
        )
        
        if result:
            print(f"✅ 上传成功!")
            print(f"  返回结果: {result}")
            
            # 检查是否添加了 [谱面碎片] 标记
            maidata_file.seek(0)
            content = maidata_file.read().decode('utf-8')
            if '[谱面碎片]' in content:
                print(f"  ✅ 标题已添加 [谱面碎片] 前缀")
            else:
                print(f"  ⚠️  未找到 [谱面碎片] 标记")
            
            return True
        else:
            print(f"❌ 上传失败")
            return False
            
    except Exception as e:
        print(f"❌ 上传异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_title_modification():
    """单独测试标题修改功能"""
    print("\n========== 测试标题修改功能 ==========")
    
    maidata_content = create_test_maidata()
    print(f"原始标题: 测试谱面")
    
    # 调用标题修改方法
    modified_content = MajdataService._modify_maidata_for_part_chart(maidata_content)
    
    # 检查结果
    if '&title=[谱面碎片]测试谱面' in modified_content:
        print(f"✅ 标题修改成功: [谱面碎片]测试谱面")
        return True
    else:
        print(f"❌ 标题修改失败")
        print(f"修改后内容:\n{modified_content[:200]}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Majdata.net 上传功能测试")
    print("=" * 60)
    
    results = {}
    
    # 测试1: 登录
    results['登录'] = test_login()
    
    if not results['登录']:
        print("\n⚠️  登录失败，跳过上传测试")
        print("\n请检查:")
        print("  1. login_credentials.env 文件是否存在")
        print("  2. MAJDATA_USERNAME 和 MAJDATA_PASSWD_HASHED 是否正确")
        print("  3. Majdata.net 服务是否可访问")
        return
    
    # 测试2: 标题修改
    results['标题修改'] = test_title_modification()
    
    # 测试3: 完整谱面上传
    results['完整谱面上传'] = test_upload_full_chart()
    
    # 测试4: 碎片谱面上传
    results['碎片谱面上传'] = test_upload_part_chart()
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")


if __name__ == '__main__':
    main()
