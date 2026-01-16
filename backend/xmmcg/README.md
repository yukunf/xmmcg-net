# Django 用户管理系统

一个基于 Django 自带用户系统的安全用户管理后端，提供 RESTful API 接口供 Vue 前端调用。

## 🚀 快速开始

### 前置条件
- Python 3.9+
- pip
- 虚拟环境（推荐）

### 安装步骤

1. **进入项目目录**
```bash
cd backend/xmmcg
```

2. **创建并激活虚拟环境**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **运行数据库迁移**
```bash
python manage.py migrate
```

5. **创建超级用户（可选，用于 Django Admin）**
```bash
python manage.py createsuperuser
```

6. **启动开发服务器**
```bash
python manage.py runserver
```

服务器将在 `http://localhost:8000` 启动

## 📁 项目结构

```
backend/xmmcg/
├── xmmcg/                    # Django 项目配置
│   ├── settings.py          # 项目设置
│   ├── urls.py              # 项目 URL 配置
│   ├── wsgi.py              # WSGI 应用
│   └── asgi.py              # ASGI 应用
├── users/                    # 用户应用
│   ├── views.py             # API 视图
│   ├── serializers.py       # 数据序列化器
│   ├── urls.py              # 应用 URL 路由
│   └── models.py            # 数据模型（使用 Django 自带 User）
├── manage.py                 # Django 管理脚本
├── db.sqlite3               # SQLite 数据库
├── requirements.txt         # 项目依赖
├── test_api.py              # API 测试脚本
├── run_server.bat           # 启动脚本（Windows）
└── API_DOCS.md              # API 文档
```

## 📚 API 文档

详细的 API 文档请查看 [API_DOCS.md](API_DOCS.md)

### 主要端点

| 方法 | 端点 | 说明 | 需要认证 |
|------|------|------|---------|
| POST | `/api/users/register/` | 用户注册 | ❌ |
| POST | `/api/users/login/` | 用户登录 | ❌ |
| POST | `/api/users/logout/` | 用户登出 | ✅ |
| GET | `/api/users/me/` | 获取当前用户信息 | ✅ |
| PUT | `/api/users/profile/` | 更新用户信息 | ✅ |
| POST | `/api/users/change-password/` | 修改密码 | ✅ |
| POST | `/api/users/check-username/` | 检查用户名可用性 | ❌ |
| POST | `/api/users/check-email/` | 检查邮箱可用性 | ❌ |

## 🔒 安全特性

### 1. 密码安全
- **最小长度**：8 个字符
- **强度验证**：不能过于简单
- **哈希算法**：Django 默认的 PBKDF2 算法
- **验证规则**：
  - 不能与用户名相似
  - 不能是常见密码
  - 不能全是数字

### 2. CSRF 保护
- 自动 CSRF Token 生成和验证
- 所有 POST/PUT/DELETE 请求都需要 Token
- Token 在 Cookie 中自动设置

### 3. 会话管理
- Django Session 认证
- Cookie-based 会话管理
- 自动会话超时

### 4. 数据验证
- 邮箱唯一性检查
- 用户名唯一性检查
- 表单数据完整性检查
- 邮箱格式验证

### 5. CORS 保护
- 限制允许的跨域源
- 仅允许特定域名访问

## 🧪 测试

### 运行自动测试

```bash
python test_api.py
```

这将测试以下功能：
- ✓ 用户注册
- ✓ 重复注册检查
- ✓ 用户登录
- ✓ 错误密码拒绝
- ✓ 获取用户信息
- ✓ 更新用户信息
- ✓ 修改密码
- ✓ 检查用户名可用性
- ✓ 检查邮箱可用性
- ✓ 用户登出
- ✓ 未认证端点保护

### 使用 curl 测试

**注册**
```bash
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
  }'
```

**登录**
```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "username": "testuser",
    "password": "SecurePass123!"
  }'
```

**获取当前用户**
```bash
curl -X GET http://localhost:8000/api/users/me/ \
  -b cookies.txt
```

## 🔧 配置说明

### settings.py 关键配置

**CORS 配置**
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",     # Vue 默认端口
    "http://localhost:5173",     # Vite 默认端口
]
```

**REST Framework 配置**
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

**密码验证规则**
```python
AUTH_PASSWORD_VALIDATORS = [
    # 不能与用户名相似
    "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    # 最小长度 8 个字符
    "django.contrib.auth.password_validation.MinimumLengthValidator",
    # 不能是常见密码
    "django.contrib.auth.password_validation.CommonPasswordValidator",
    # 不能全是数字
    "django.contrib.auth.password_validation.NumericPasswordValidator",
]
```

## 🔌 Vue 前端集成

### 安装 axios

```bash
npm install axios
```

### 创建 API 服务

```javascript
// src/services/auth.js
import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api/users',
    withCredentials: true, // 重要：允许带上 Cookie
});

export const authService = {
    register: (data) => api.post('/register/', data),
    login: (data) => api.post('/login/', data),
    logout: () => api.post('/logout/'),
    getCurrentUser: () => api.get('/me/'),
    updateProfile: (data) => api.put('/profile/', data),
    changePassword: (data) => api.post('/change-password/', data),
    checkUsername: (username) => api.post('/check-username/', { username }),
    checkEmail: (email) => api.post('/check-email/', { email }),
};
```

### 在 Vue 组件中使用

```javascript
// 注册
import { authService } from '@/services/auth';

async function register() {
    try {
        const response = await authService.register({
            username: 'john_doe',
            email: 'john@example.com',
            password: 'SecurePass123!',
            password_confirm: 'SecurePass123!',
        });
        console.log('注册成功:', response.data);
    } catch (error) {
        console.error('注册失败:', error.response.data);
    }
}

// 登录
async function login() {
    try {
        const response = await authService.login({
            username: 'john_doe',
            password: 'SecurePass123!',
        });
        console.log('登录成功:', response.data);
    } catch (error) {
        console.error('登录失败:', error.response.data);
    }
}
```

## 🚀 生产环境部署

### 1. 修改 settings.py

```python
# 禁用调试模式
DEBUG = False

# 设置允许的主机
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']

# 使用环境变量设置 SECRET_KEY
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

# 强制使用 HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 2. 收集静态文件

```bash
python manage.py collectstatic --noinput
```

### 3. 使用 Gunicorn 运行

```bash
pip install gunicorn
gunicorn xmmcg.wsgi:application --bind 0.0.0.0:8000
```

### 4. 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📦 依赖包说明

| 包名 | 版本 | 说明 |
|------|------|------|
| Django | 6.0.1 | Web 框架 |
| djangorestframework | 3.14.0 | REST API 框架 |
| django-cors-headers | 4.3.1 | CORS 支持 |
| python-decouple | 3.8 | 环境变量管理 |

## 🐛 常见问题

### Q: 跨域请求失败？
**A:** 确保：
1. `django-cors-headers` 已安装
2. `CorsMiddleware` 在 MIDDLEWARE 列表的最上面
3. 请求的源在 `CORS_ALLOWED_ORIGINS` 中
4. 前端请求使用 `withCredentials: true`

### Q: CSRF Token 问题？
**A:** 
1. 使用 axios 时自动处理（从 Cookie 读取）
2. 或在请求头中手动添加：`X-CSRFToken: <token>`

### Q: 密码验证太严格？
**A:** 在 settings.py 中修改 `AUTH_PASSWORD_VALIDATORS`

### Q: 如何实现 Token-based 认证？
**A:** 需要安装 `djangorestframework-simplejwt`，详见官方文档

## 📝 许可证

MIT

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请在 GitHub 上提交 Issue。
