# 快速参考指南

## 🚀 快速启动

### Windows

```bash
# 进入项目目录
cd backend\xmmcg

# 运行启动脚本
run_server.bat
```

### Linux/Mac

```bash
# 进入项目目录
cd backend/xmmcg

# 激活虚拟环境
source ../../.venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行迁移
python manage.py migrate

# 启动服务器
python manage.py runserver
```

## 📋 常用命令

### 数据库操作

```bash
# 查看待应用的迁移
python manage.py showmigrations

# 创建新的迁移
python manage.py makemigrations

# 应用迁移
python manage.py migrate

# 重置数据库（删除所有数据）
python manage.py migrate users zero
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser

# 删除用户
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.filter(username='username').delete()
>>> exit()
```

### 开发命令

```bash
# 启动开发服务器
python manage.py runserver

# 启动服务器并指定端口
python manage.py runserver 0.0.0.0:8080

# 运行 Django shell（可以交互式操作数据库）
python manage.py shell

# 运行测试
python test_api.py

# 检查代码问题
python manage.py check

# 生成静态文件
python manage.py collectstatic
```

## 🔌 API 快速参考

### 认证相关

#### 注册
```
POST /api/users/register/
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

#### 登录
```
POST /api/users/login/
Content-Type: application/json

{
  "username": "john_doe",
  "password": "SecurePass123!"
}
```

#### 登出
```
POST /api/users/logout/
```

### 用户信息

#### 获取当前用户
```
GET /api/users/me/
```

#### 更新用户信息
```
PUT /api/users/profile/
Content-Type: application/json

{
  "email": "newemail@example.com",
  "first_name": "Johnny",
  "last_name": "Smith"
}
```

#### 修改密码
```
POST /api/users/change-password/
Content-Type: application/json

{
  "old_password": "OldPassword123!",
  "new_password": "NewPassword456!",
  "new_password_confirm": "NewPassword456!"
}
```

### 验证

#### 检查用户名可用性
```
POST /api/users/check-username/
Content-Type: application/json

{
  "username": "new_user"
}
```

#### 检查邮箱可用性
```
POST /api/users/check-email/
Content-Type: application/json

{
  "email": "user@example.com"
}
```

## 📁 重要文件位置

| 文件 | 说明 |
|------|------|
| [xmmcg/settings.py](xmmcg/settings.py) | 项目设置（CORS、认证等） |
| [xmmcg/urls.py](xmmcg/urls.py) | 项目 URL 路由 |
| [users/views.py](users/views.py) | API 视图函数 |
| [users/serializers.py](users/serializers.py) | 数据序列化器 |
| [users/urls.py](users/urls.py) | 用户应用 URL 路由 |
| [API_DOCS.md](API_DOCS.md) | 详细 API 文档 |
| [README.md](README.md) | 项目说明文档 |

## 🔍 调试技巧

### 查看数据库中的用户

```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> users = User.objects.all()
>>> for user in users:
...     print(f"用户名: {user.username}, 邮箱: {user.email}")
>>> exit()
```

### 查看当前的 CORS 配置

```bash
python manage.py shell
>>> from django.conf import settings
>>> print(settings.CORS_ALLOWED_ORIGINS)
```

### 测试密码验证

```bash
python manage.py shell
>>> from django.contrib.auth.password_validation import validate_password
>>> try:
...     validate_password("password")
... except Exception as e:
...     print(e)
```

## 🌐 CORS 跨域配置

编辑 [xmmcg/settings.py](xmmcg/settings.py)，找到 `CORS_ALLOWED_ORIGINS`：

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",      # Vue 默认端口
    "http://localhost:5173",      # Vite 默认端口
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    # 添加更多允许的源
    # "https://your-domain.com",
]
```

## 🔐 开发 vs 生产环境配置

### 开发环境（当前）
- DEBUG = True
- SQLite 数据库
- 任何主机都可访问
- CORS 允许 localhost

### 生产环境需要修改的配置

```python
# 禁用调试
DEBUG = False

# 设置允许的主机
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

# 随机的 SECRET_KEY
SECRET_KEY = 'your-random-secret-key-here'

# 强制 HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# 使用生产数据库（如 PostgreSQL）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'xmmcg_db',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 📊 项目统计

- **用户相关 API 端点**: 8 个
- **包含的功能**: 注册、登录、登出、获取用户、修改信息、改密码、检查可用性
- **使用的 Django 应用**: 6 个（admin, auth, contenttypes, sessions, messages, staticfiles）
- **使用的第三方库**: 2 个（djangorestframework, django-cors-headers）

## 💡 最佳实践

1. **始终在开发中启用 HTTPS**（即使在本地，也可以使用自签名证书）
2. **定期备份数据库**
3. **记录所有用户操作**（可以添加日志记录）
4. **使用环境变量存储敏感信息**
5. **在生产环境使用更强大的认证方式**（如 JWT）
6. **添加速率限制**（防止暴力破解）
7. **定期更新依赖包**

## 🆘 问题排查

### 问题：CORS 错误
```
Access to XMLHttpRequest ... has been blocked by CORS policy
```
**解决**:
1. 检查 CORS_ALLOWED_ORIGINS 配置
2. 确保请求使用 `withCredentials: true`
3. 检查 CorsMiddleware 是否在最上面

### 问题：认证失败
```
{"detail":"Authentication credentials were not provided."}
```
**解决**:
1. 确保已登录
2. 检查 Cookie 是否保存
3. 检查 axios 配置中是否有 `withCredentials: true`

### 问题：CSRF Token 错误
```
{"detail":"CSRF Failed: CSRF token missing."}
```
**解决**:
1. axios 会自动处理 CSRF Token
2. 或在请求头手动添加 `X-CSRFToken`

---

更多信息请查看 [README.md](README.md) 和 [API_DOCS.md](API_DOCS.md)
