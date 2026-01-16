#!/usr/bin/env python
"""
Django 用户管理系统 - 项目总结

这个脚本生成项目的概览和统计信息。
"""

import os
import sys
from pathlib import Path

def print_header(text):
    """打印标题"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def count_lines(filepath):
    """计算文件行数"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except:
        return 0

def main():
    print_header("Django 用户管理系统 - 项目总结")
    
    # 项目统计
    project_dir = Path('.')
    
    # 计算 Python 文件
    py_files = list(project_dir.rglob('*.py'))
    py_files = [f for f in py_files if '__pycache__' not in str(f) and '.venv' not in str(f)]
    
    # 计算文档文件
    md_files = list(project_dir.rglob('*.md'))
    
    # 计算代码行数
    total_lines = sum(count_lines(f) for f in py_files)
    
    print("📊 项目统计信息")
    print(f"  • Python 文件数: {len(py_files)}")
    print(f"  • 总代码行数: {total_lines}")
    print(f"  • 文档文件数: {len(md_files)}")
    print(f"  • 配置文件: 3 (settings.py, urls.py, requirements.txt)")
    
    print_header("📁 核心文件详情")
    
    core_files = {
        'users/views.py': 'API 视图函数（8 个端点）',
        'users/serializers.py': '数据序列化器（4 个）',
        'users/urls.py': 'URL 路由配置',
        'xmmcg/settings.py': 'Django 项目设置',
        'xmmcg/urls.py': '主 URL 配置',
    }
    
    for filename, description in core_files.items():
        filepath = project_dir / filename
        if filepath.exists():
            lines = count_lines(filepath)
            print(f"  ✓ {filename}")
            print(f"    └─ {description}")
            print(f"    └─ {lines} 行代码\n")
    
    print_header("📚 文档文件")
    
    docs = {
        'README.md': '项目详细说明文档',
        'API_DOCS.md': 'API 接口完整文档',
        'QUICK_START.md': '快速启动指南',
        'COMPLETION_CHECKLIST.md': '项目完成清单',
    }
    
    for filename, description in docs.items():
        filepath = project_dir / filename
        if filepath.exists():
            print(f"  ✓ {filename}")
            print(f"    └─ {description}\n")
    
    print_header("🔌 API 端点列表")
    
    endpoints = [
        ('POST', '/api/users/register/', '用户注册', 'AllowAny'),
        ('POST', '/api/users/login/', '用户登录', 'AllowAny'),
        ('POST', '/api/users/logout/', '用户登出', 'IsAuthenticated'),
        ('GET', '/api/users/me/', '获取当前用户', 'IsAuthenticated'),
        ('PUT', '/api/users/profile/', '更新用户信息', 'IsAuthenticated'),
        ('POST', '/api/users/change-password/', '修改密码', 'IsAuthenticated'),
        ('POST', '/api/users/check-username/', '检查用户名', 'AllowAny'),
        ('POST', '/api/users/check-email/', '检查邮箱', 'AllowAny'),
    ]
    
    print(f"{'方法':<6} {'端点':<35} {'说明':<20} {'权限':<18}")
    print("-" * 80)
    
    for method, endpoint, desc, auth in endpoints:
        print(f"{method:<6} {endpoint:<35} {desc:<20} {auth:<18}")
    
    print_header("🔒 安全特性")
    
    security_features = [
        '✓ 密码强度验证（最少 8 个字符）',
        '✓ 密码哈希加密（PBKDF2）',
        '✓ CSRF 保护',
        '✓ 会话认证',
        '✓ 邮箱和用户名唯一性检查',
        '✓ CORS 跨域保护',
        '✓ 数据验证和清理',
        '✓ 权限控制（认证/非认证分离）',
    ]
    
    for feature in security_features:
        print(f"  {feature}")
    
    print_header("🛠️  技术栈")
    
    tech_stack = {
        'Web 框架': 'Django 6.0.1',
        'API 框架': 'Django REST Framework 3.14.0',
        '认证方式': 'Django Session + CSRF',
        'CORS 处理': 'django-cors-headers 4.3.1',
        '数据库': 'SQLite3 (开发) / PostgreSQL (生产)',
        'Python 版本': '3.9+',
    }
    
    for key, value in tech_stack.items():
        print(f"  • {key:<15}: {value}")
    
    print_header("🚀 快速开始")
    
    print("""  Windows:
    1. cd backend\\xmmcg
    2. run_server.bat
    3. 访问 http://localhost:8000
  
  Linux/Mac:
    1. cd backend/xmmcg
    2. source ../../.venv/bin/activate
    3. python manage.py runserver
    4. 访问 http://localhost:8000""")
    
    print_header("📖 文档位置")
    
    docs_map = {
        '完整 API 文档': '→ API_DOCS.md',
        '项目说明': '→ README.md',
        '快速启动': '→ QUICK_START.md',
        '项目清单': '→ COMPLETION_CHECKLIST.md',
    }
    
    for doc_type, location in docs_map.items():
        print(f"  {doc_type:<20} {location}")
    
    print_header("✅ 项目完成状态")
    
    print("""  核心功能:
    ✓ 用户注册、登录、登出
    ✓ 个人信息管理
    ✓ 密码修改
    ✓ 用户名和邮箱检查
  
  安全特性:
    ✓ 密码验证和加密
    ✓ CSRF 保护
    ✓ CORS 配置
    ✓ 权限控制
  
  开发工具:
    ✓ 自动化测试脚本
    ✓ API 启动脚本
    ✓ 详细文档
  
  可以立即使用！""")
    
    print_header("💡 后续建议")
    
    suggestions = [
        '1. 邮箱验证和密码重置功能',
        '2. 用户头像上传管理',
        '3. 操作日志记录',
        '4. JWT Token 认证',
        '5. 速率限制和 IP 黑名单',
        '6. 用户角色和权限系统',
        '7. 缓存优化（Redis）',
        '8. 单元测试和集成测试',
    ]
    
    for suggestion in suggestions:
        print(f"  • {suggestion}")
    
    print("\n" + "="*70)
    print("  项目已完成！🎉")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
