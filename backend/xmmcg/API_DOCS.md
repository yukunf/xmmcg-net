# Django 用户管理 API 文档

## 概述
这是一个基于 Django 自带用户系统的安全用户管理后端，使用 Django REST Framework 提供 API 接口。

## 基础配置

- **基础 URL**: `http://localhost:8000/api/users/`
- **认证方式**: Django Session 认证
- **请求格式**: JSON
- **响应格式**: JSON

## API 端点

### 1. 用户注册
**URL**: `/api/users/register/`  
**方法**: `POST`  
**权限**: 任何人

**请求体**:
```json
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
}
```

**成功响应** (201):
```json
{
    "success": true,
    "message": "注册成功",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": true,
        "date_joined": "2024-01-16T10:00:00Z"
    }
}
```

**错误响应** (400):
```json
{
    "success": false,
    "errors": {
        "username": ["用户名已存在"],
        "email": ["该邮箱已被注册"],
        "password": ["密码过于简单"]
    }
}
```

---

### 2. 用户登录
**URL**: `/api/users/login/`  
**方法**: `POST`  
**权限**: 任何人

**请求体**:
```json
{
    "username": "john_doe",
    "password": "SecurePass123!"
}
```

**成功响应** (200):
```json
{
    "success": true,
    "message": "登录成功",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": true,
        "date_joined": "2024-01-16T10:00:00Z"
    }
}
```

**错误响应** (401):
```json
{
    "success": false,
    "message": "用户名或密码错误"
}
```

---

### 3. 用户登出
**URL**: `/api/users/logout/`  
**方法**: `POST`  
**权限**: 需要认证

**请求体**: 无

**成功响应** (200):
```json
{
    "success": true,
    "message": "登出成功"
}
```

---

### 4. 获取当前用户信息
**URL**: `/api/users/me/`  
**方法**: `GET`  
**权限**: 需要认证

**请求体**: 无

**成功响应** (200):
```json
{
    "success": true,
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "is_active": true,
        "date_joined": "2024-01-16T10:00:00Z"
    }
}
```

---

### 5. 更新用户个人信息
**URL**: `/api/users/profile/`  
**方法**: `PUT` 或 `PATCH`  
**权限**: 需要认证

**请求体**:
```json
{
    "email": "newemail@example.com",
    "first_name": "Johnny",
    "last_name": "Smith"
}
```

**成功响应** (200):
```json
{
    "success": true,
    "message": "个人信息已更新",
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "newemail@example.com",
        "first_name": "Johnny",
        "last_name": "Smith",
        "is_active": true,
        "date_joined": "2024-01-16T10:00:00Z"
    }
}
```

---

### 6. 修改密码
**URL**: `/api/users/change-password/`  
**方法**: `POST`  
**权限**: 需要认证

**请求体**:
```json
{
    "old_password": "OldPassword123!",
    "new_password": "NewPassword456!",
    "new_password_confirm": "NewPassword456!"
}
```

**成功响应** (200):
```json
{
    "success": true,
    "message": "密码已更改"
}
```

**错误响应** (400):
```json
{
    "success": false,
    "message": "旧密码错误"
}
```

---

### 7. 检查用户名可用性
**URL**: `/api/users/check-username/`  
**方法**: `POST`  
**权限**: 任何人

**请求体**:
```json
{
    "username": "new_user"
}
```

**成功响应** (200):
```json
{
    "success": true,
    "available": true,
    "username": "new_user"
}
```

或

```json
{
    "success": true,
    "available": false,
    "username": "john_doe"
}
```

---

### 8. 检查邮箱可用性
**URL**: `/api/users/check-email/`  
**方法**: `POST`  
**权限**: 任何人

**请求体**:
```json
{
    "email": "user@example.com"
}
```

**成功响应** (200):
```json
{
    "success": true,
    "available": true,
    "email": "user@example.com"
}
```

---

## 安全特性

1. **密码安全**
   - 最小长度 8 个字符
   - 密码强度验证（不能过于简单）
   - 使用 Django 的密码哈希算法

2. **CSRF 保护**
   - 所有 POST/PUT/DELETE 请求都需要 CSRF Token
   - 在 Cookie 中自动设置

3. **会话认证**
   - 使用 Django Session 管理用户认证状态
   - 支持 CORS 跨域请求

4. **数据验证**
   - 邮箱唯一性检查
   - 用户名唯一性检查
   - 表单数据完整性检查

## 安装与运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 迁移数据库
```bash
cd backend/xmmcg
python manage.py migrate
```

### 3. 创建超级用户（可选）
```bash
python manage.py createsuperuser
```

### 4. 运行开发服务器
```bash
python manage.py runserver
```

服务器将在 `http://localhost:8000` 启动

## Vue 前端集成示例

### 安装 axios
```bash
npm install axios
```

### 创建 API 服务
```javascript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/users';

const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true, // 重要：允许跨域请求带上 Cookie
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

### 使用示例
```javascript
// 注册
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

// 登录
try {
    const response = await authService.login({
        username: 'john_doe',
        password: 'SecurePass123!',
    });
    console.log('登录成功:', response.data);
} catch (error) {
    console.error('登录失败:', error.response.data);
}
```

## 注意事项

1. **CORS 配置**：在 settings.py 中已配置允许 `localhost:3000` 和 `localhost:5173` 访问。如需其他源，请更新 `CORS_ALLOWED_ORIGINS`。

2. **生产环境**：
   - 将 `DEBUG = False`
   - 更改 `SECRET_KEY` 为随机值
   - 设置 `ALLOWED_HOSTS`
   - 使用 HTTPS

3. **数据库**：默认使用 SQLite，生产环境建议使用 PostgreSQL 或 MySQL。

## 常见问题

**Q: 如何获取 CSRF Token？**  
A: CSRF Token 会自动在 Cookie 中设置，axios 会自动从 Cookie 中读取 `csrftoken` 并在请求头中发送。

**Q: 如何在 Vue 中持久化用户登录状态？**  
A: 可以在 Vue Store（如 Pinia）中存储用户信息，在应用启动时调用 `/me/` 端点验证。

**Q: 如何实现"记住我"功能？**  
A: 可以通过设置更长的会话超时时间或实现 Token-based 认证（需要修改当前实现）。
