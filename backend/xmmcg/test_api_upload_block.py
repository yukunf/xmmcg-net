"""
测试谱面上传API阻止功能
"""
import requests
import json

# 配置
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

# 从上面的测试结果获取
USERNAME = "test_upload_1768736160.22605"
PASSWORD = "test123"  # 默认密码
BID_RESULT_1_ID = 217  # 第一阶段中标结果ID
BID_RESULT_2_ID = 218  # 第二阶段中标结果ID

def test_upload_blocking():
    """测试谱面上传阻止功能"""
    
    print("="*70)
    print("测试谱面上传API阻止功能")
    print("="*70)
    
    # 1. 登录获取session
    print("\n1. 登录用户...")
    session = requests.Session()
    
    # 先获取CSRF token
    csrf_response = session.get(f"{API_URL}/users/csrf/")
    print(f"   CSRF响应: {csrf_response.status_code}")
    
    # 登录
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    login_response = session.post(
        f"{API_URL}/users/login/",
        json=login_data,
        headers={'X-CSRFToken': session.cookies.get('csrftoken')}
    )
    
    if login_response.status_code == 200:
        print(f"   ✓ 登录成功")
    else:
        print(f"   ✗ 登录失败: {login_response.status_code}")
        print(f"   响应: {login_response.text}")
        return
    
    # 2. 测试第一阶段上传（应被阻止）
    print(f"\n2. 测试第一阶段上传阻止 (BidResult ID: {BID_RESULT_1_ID})...")
    
    # 创建假的表单数据
    files = {
        'audio_file': ('test.mp3', b'fake audio', 'audio/mpeg'),
        'cover_image': ('test.jpg', b'fake image', 'image/jpeg'),
        'chart_file': ('maidata.txt', b'&des=TestDesigner\n&title=Test\n[0]E,2,,,', 'text/plain'),
    }
    data = {
        'designer': 'TestDesigner'
    }
    
    upload_response_1 = session.post(
        f"{API_URL}/songs/charts/{BID_RESULT_1_ID}/submit/",
        files=files,
        data=data,
        headers={'X-CSRFToken': session.cookies.get('csrftoken')}
    )
    
    print(f"   响应状态码: {upload_response_1.status_code}")
    
    if upload_response_1.status_code == 400:
        print(f"   ✓ 正确阻止了第一阶段重复上传")
        try:
            error_data = upload_response_1.json()
            print(f"   错误信息: {error_data.get('message', error_data)}")
        except:
            print(f"   响应文本: {upload_response_1.text[:200]}")
    else:
        print(f"   ✗ 未能正确阻止上传")
        print(f"   响应: {upload_response_1.text[:200]}")
    
    # 3. 测试第二阶段上传（应被阻止）
    print(f"\n3. 测试第二阶段上传阻止 (BidResult ID: {BID_RESULT_2_ID})...")
    
    upload_response_2 = session.post(
        f"{API_URL}/songs/charts/{BID_RESULT_2_ID}/submit/",
        files=files,
        data=data,
        headers={'X-CSRFToken': session.cookies.get('csrftoken')}
    )
    
    print(f"   响应状态码: {upload_response_2.status_code}")
    
    if upload_response_2.status_code == 400:
        print(f"   ✓ 正确阻止了第二阶段重复上传")
        try:
            error_data = upload_response_2.json()
            print(f"   错误信息: {error_data.get('message', error_data)}")
        except:
            print(f"   响应文本: {upload_response_2.text[:200]}")
    else:
        print(f"   ✗ 未能正确阻止上传")
        print(f"   响应: {upload_response_2.text[:200]}")
    
    # 总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    
    stage1_blocked = upload_response_1.status_code == 400
    stage2_blocked = upload_response_2.status_code == 400
    
    print(f"\n第一阶段阻止: {'✓ 通过' if stage1_blocked else '✗ 失败'}")
    print(f"第二阶段阻止: {'✓ 通过' if stage2_blocked else '✗ 失败'}")
    
    if stage1_blocked and stage2_blocked:
        print("\n✓✓✓ 所有测试通过！谱面上传阻止功能正常工作 ✓✓✓")
    else:
        print("\n✗✗✗ 部分测试失败，请检查后端逻辑 ✗✗✗")

if __name__ == '__main__':
    try:
        test_upload_blocking()
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器，请确保Django服务器正在运行")
        print(f"  服务器地址: {BASE_URL}")
    except Exception as e:
        print(f"✗ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
