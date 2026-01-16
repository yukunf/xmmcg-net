#!/usr/bin/env python
"""
Django 用户管理 API 测试脚本
用于测试所有用户管理端点

使用方法:
1. 启动 Django 服务器: python manage.py runserver
2. 在另一个终端运行此脚本: python test_api.py
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

# API 基础 URL
BASE_URL = 'http://localhost:8000/api/users'

# 用于存储会话的 session 对象
session = requests.Session()

# 测试用户数据
TEST_USER = {
    'username': f'testuser_{int(datetime.now().timestamp())}',
    'email': f'test_{int(datetime.now().timestamp())}@example.com',
    'password': 'TestPassword123!',
    'first_name': 'Test',
    'last_name': 'User'
}

def print_section(title):
    """打印测试分节标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")

def print_response(response, endpoint):
    """打印响应信息"""
    print(f"【{endpoint}】")
    print(f"状态码: {response.status_code}")
    try:
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"响应: {response.text}")
    print()

def test_register():
    """测试用户注册"""
    print_section("1. 测试用户注册")
    
    # 测试正常注册
    data = {
        **TEST_USER,
        'password_confirm': TEST_USER['password']
    }
    
    response = session.post(f'{BASE_URL}/register/', json=data)
    print_response(response, 'POST /register/')
    
    if response.status_code == 201:
        print("✓ 注册成功")
        return True
    else:
        print("✗ 注册失败")
        return False

def test_register_duplicate():
    """测试重复注册（应该失败）"""
    print_section("2. 测试重复用户名注册（应该失败）")
    
    data = {
        **TEST_USER,
        'password_confirm': TEST_USER['password']
    }
    
    response = session.post(f'{BASE_URL}/register/', json=data)
    print_response(response, 'POST /register/')
    
    if response.status_code == 400:
        print("✓ 正确拒绝了重复注册")
        return True
    else:
        print("✗ 应该返回 400 错误")
        return False

def test_login():
    """测试用户登录"""
    print_section("3. 测试用户登录")
    
    data = {
        'username': TEST_USER['username'],
        'password': TEST_USER['password']
    }
    
    response = session.post(f'{BASE_URL}/login/', json=data)
    print_response(response, 'POST /login/')
    
    if response.status_code == 200:
        print("✓ 登录成功")
        return True
    else:
        print("✗ 登录失败")
        return False

def test_login_wrong_password():
    """测试错误密码登录（应该失败）"""
    print_section("4. 测试错误密码登录（应该失败）")
    
    data = {
        'username': TEST_USER['username'],
        'password': 'WrongPassword123!'
    }
    
    response = session.post(f'{BASE_URL}/login/', json=data)
    print_response(response, 'POST /login/')
    
    if response.status_code == 401:
        print("✓ 正确拒绝了错误密码")
        return True
    else:
        print("✗ 应该返回 401 错误")
        return False

def test_get_current_user():
    """测试获取当前用户信息"""
    print_section("5. 测试获取当前用户信息")
    
    response = session.get(f'{BASE_URL}/me/')
    print_response(response, 'GET /me/')
    
    if response.status_code == 200:
        print("✓ 成功获取用户信息")
        return True
    else:
        print("✗ 获取用户信息失败")
        return False

def test_update_profile():
    """测试更新用户信息"""
    print_section("6. 测试更新用户个人信息")
    
    data = {
        'first_name': 'Updated',
        'last_name': 'Name',
        'email': f'updated_{int(datetime.now().timestamp())}@example.com'
    }
    
    response = session.put(f'{BASE_URL}/profile/', json=data)
    print_response(response, 'PUT /profile/')
    
    if response.status_code == 200:
        print("✓ 成功更新用户信息")
        return True
    else:
        print("✗ 更新用户信息失败")
        return False

def test_change_password():
    """测试修改密码"""
    print_section("7. 测试修改密码")
    
    new_password = 'NewPassword456!'
    
    data = {
        'old_password': TEST_USER['password'],
        'new_password': new_password,
        'new_password_confirm': new_password
    }
    
    response = session.post(f'{BASE_URL}/change-password/', json=data)
    print_response(response, 'POST /change-password/')
    
    if response.status_code == 200:
        print("✓ 成功修改密码")
        # 更新测试用户的密码
        TEST_USER['password'] = new_password
        return True
    else:
        print("✗ 修改密码失败")
        return False

def test_check_username_availability():
    """测试检查用户名可用性"""
    print_section("8. 测试检查用户名可用性")
    
    # 检查已存在的用户名
    print("检查已存在的用户名:")
    data = {'username': TEST_USER['username']}
    response = session.post(f'{BASE_URL}/check-username/', json=data)
    print_response(response, 'POST /check-username/')
    
    # 检查不存在的用户名
    print("检查不存在的用户名:")
    data = {'username': 'definitely_not_exist_12345'}
    response = session.post(f'{BASE_URL}/check-username/', json=data)
    print_response(response, 'POST /check-username/')
    
    return True

def test_check_email_availability():
    """测试检查邮箱可用性"""
    print_section("9. 测试检查邮箱可用性")
    
    # 检查已存在的邮箱
    print("检查已存在的邮箱:")
    data = {'email': TEST_USER['email']}
    response = session.post(f'{BASE_URL}/check-email/', json=data)
    print_response(response, 'POST /check-email/')
    
    # 检查不存在的邮箱
    print("检查不存在的邮箱:")
    data = {'email': f'notexist_{int(datetime.now().timestamp())}@example.com'}
    response = session.post(f'{BASE_URL}/check-email/', json=data)
    print_response(response, 'POST /check-email/')
    
    return True

def test_logout():
    """测试用户登出"""
    print_section("10. 测试用户登出")
    
    response = session.post(f'{BASE_URL}/logout/')
    print_response(response, 'POST /logout/')
    
    if response.status_code == 200:
        print("✓ 成功登出")
        return True
    else:
        print("✗ 登出失败")
        return False

def test_protected_endpoint_without_auth():
    """测试未认证访问受保护端点"""
    print_section("11. 测试未认证访问受保护端点（应该失败）")
    
    # 创建新的 session（没有认证）
    new_session = requests.Session()
    
    response = new_session.get(f'{BASE_URL}/me/')
    print_response(response, 'GET /me/ (未认证)')
    
    if response.status_code == 401:
        print("✓ 正确拒绝了未认证请求")
        return True
    else:
        print("✗ 应该返回 401 错误")
        return False

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  Django 用户管理 API 测试")
    print("=" * 60)
    print(f"\n基础 URL: {BASE_URL}")
    print(f"测试用户: {TEST_USER['username']}")
    print(f"测试邮箱: {TEST_USER['email']}\n")
    
    try:
        # 检查服务器是否运行
        response = session.get(f'{BASE_URL}/register/')
        print(f"✓ 服务器已连接 (状态码: {response.status_code})\n")
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器")
        print("请确保 Django 服务器正在运行: python manage.py runserver\n")
        return
    
    results = []
    
    # 运行所有测试
    try:
        results.append(('用户注册', test_register()))
        results.append(('重复注册失败检查', test_register_duplicate()))
        results.append(('用户登录', test_login()))
        results.append(('错误密码登录失败检查', test_login_wrong_password()))
        results.append(('获取当前用户', test_get_current_user()))
        results.append(('更新用户信息', test_update_profile()))
        results.append(('修改密码', test_change_password()))
        results.append(('检查用户名可用性', test_check_username_availability()))
        results.append(('检查邮箱可用性', test_check_email_availability()))
        results.append(('用户登出', test_logout()))
        results.append(('未认证端点保护', test_protected_endpoint_without_auth()))
    except Exception as e:
        print(f"\n✗ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 打印测试总结
    print_section("测试总结")
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n总体: {passed}/{total} 测试通过")

if __name__ == '__main__':
    main()
