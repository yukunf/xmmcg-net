# XMMCG 完整 API 文档

> 全功能 Django REST API 服务文档，包含用户认证、虚拟货币系统和歌曲管理模块

**最后更新**: 2026-01-16  
**API 版本**: 1.0  
**Django 版本**: 6.0.1  
**框架**: Django REST Framework 3.14.0

---

## 📑 目录

1. [概述](#概述)
2. [基础配置](#基础配置)
3. [用户认证 API](#用户认证-api)
4. [虚拟货币 API](#虚拟货币-api)
5. [歌曲管理 API](#歌曲管理-api)
6. [错误处理](#错误处理)
7. [安全特性](#安全特性)
8. [前端集成](#前端集成)
9. [常见问题](#常见问题)

---

## 概述

XMMCG 是一个完整的用户内容管理后端系统，提供以下功能：

✅ **用户管理** - 注册、登录、个人信息管理  
✅ **虚拟货币** - Token 系统，用于竞标、支付等  
✅ **歌曲管理** - 用户歌曲上传、分享、浏览  
✅ **文件处理** - 自动去重、大小限制、格式验证  
✅ **权限控制** - 基于会话的认证和授权  

### 核心特性

- **安全认证**: Django Session + CSRF 保护
- **文件管理**: 自动重命名、哈希去重、垃圾清理
- **数据验证**: 严格的输入验证和业务逻辑检查
- **跨域支持**: CORS 配置已启用
- **分页支持**: 所有列表端点都支持分页

---

## 基础配置

### 环境信息

| 配置 | 值 |
|------|-----|
| **基础 URL** | `http://localhost:8000/api/` |
| **认证方式** | Django Session（Cookie-based） |
| **请求格式** | JSON / multipart/form-data |
| **响应格式** | JSON |
| **CORS** | ✅ 启用（localhost:3000, 5173） |

### 通用请求头

```http
Content-Type: application/json
Cookie: sessionid=YOUR_SESSION_ID  // 登录后自动设置
X-CSRFToken: YOUR_CSRF_TOKEN        // POST/PUT/DELETE 需要
```

### 通用响应格式

**成功响应**:
```json
{
  "success": true,
  "message": "操作成功",
  "data": { ... }
}
```

**错误响应**:
```json
{
  "success": false,
  "message": "错误信息",
  "errors": { ... }
}
```

---

# 用户认证 API

**基础 URL**: `/api/users/`  
**功能**: 用户注册、登录、个人信息管理

## 1. 用户注册

创建新用户账户。

**请求**
```http
POST /api/users/register/
Content-Type: application/json
```

**请求体**:
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!"
}
```

**参数说明**:
| 参数 | 类型 | 说明 |
|------|------|------|
| username | string | 用户名，唯一，3-150 字符 |
| email | string | 邮箱，唯一，有效邮箱格式 |
| password | string | 密码，最少 8 字符，需要包含字母和数字 |
| password_confirm | string | 确认密码，必须与 password 相同 |

**成功响应** (201 Created):
```json
{
  "success": true,
  "message": "注册成功",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "is_active": true,
    "date_joined": "2026-01-16T14:50:45.229004Z",
    "token": 0
  }
}
```

**错误响应** (400):
```json
{
  "success": false,
  "errors": {
    "username": ["用户已存在"],
    "email": ["该邮箱已注册"],
    "password": ["密码过于简单"]
  }
}
```

**cURL 示例**:
```bash
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
  }'
```

---

## 2. 用户登录

验证用户凭证并建立会话。

**请求**
```http
POST /api/users/login/
Content-Type: application/json
```

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
    "is_active": true,
    "date_joined": "2026-01-16T14:50:45.229004Z",
    "token": 0
  }
}
```

**错误响应** (403):
```json
{
  "success": false,
  "message": "用户名或密码错误"
}
```

**cURL 示例**:
```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"username": "john_doe", "password": "SecurePass123!"}'
```

---

## 3. 用户登出

销毁当前会话。

**请求**
```http
POST /api/users/logout/
Authorization: 需要认证
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "登出成功"
}
```

**cURL 示例**:
```bash
curl -X POST http://localhost:8000/api/users/logout/ \
  -b cookies.txt
```

---

## 4. 获取当前用户信息

获取已认证用户的详细信息（包含 token 余额）。

**请求**
```http
GET /api/users/me/
Authorization: 需要认证
```

**成功响应** (200):
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "is_active": true,
    "date_joined": "2026-01-16T14:50:45.229004Z",
    "token": 500
  }
}
```

**cURL 示例**:
```bash
curl -X GET http://localhost:8000/api/users/me/ \
  -b cookies.txt
```

---

## 5. 更新用户个人信息

修改用户的邮箱等个人信息（用户名不可修改）。

**请求**
```http
PUT /api/users/profile/
Authorization: 需要认证
Content-Type: application/json
```

**请求体**:
```json
{
  "email": "newemail@example.com"
}
```

**可修改字段**:
- `email` - 邮箱地址（唯一）

**成功响应** (200):
```json
{
  "success": true,
  "message": "个人信息已更新",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "newemail@example.com",
    "is_active": true,
    "date_joined": "2026-01-16T14:50:45.229004Z",
    "token": 500
  }
}
```

---

## 6. 修改密码

修改用户账户密码，需要验证旧密码。

**请求**
```http
POST /api/users/change-password/
Authorization: 需要认证
Content-Type: application/json
```

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

## 7. 检查用户名可用性

检查用户名是否已被注册。

**请求**
```http
POST /api/users/check-username/
Content-Type: application/json
```

**请求体**:
```json
{
  "username": "john_doe"
}
```

**可用时的响应** (200):
```json
{
  "success": true,
  "available": true,
  "username": "john_doe"
}
```

**已被占用时的响应** (200):
```json
{
  "success": true,
  "available": false,
  "username": "john_doe"
}
```

---

## 8. 检查邮箱可用性

检查邮箱是否已被注册。

**请求**
```http
POST /api/users/check-email/
Content-Type: application/json
```

**请求体**:
```json
{
  "email": "user@example.com"
}
```

**可用时的响应** (200):
```json
{
  "success": true,
  "available": true,
  "email": "user@example.com"
}
```

**已被占用时的响应** (200):
```json
{
  "success": true,
  "available": false,
  "email": "user@example.com"
}
```

---

# 虚拟货币 API

**基础 URL**: `/api/users/token/`  
**功能**: Token（虚拟货币）查询和管理

## 1. 获取 Token 余额

查询当前用户的 token 余额。

**请求**
```http
GET /api/users/token/
Authorization: 需要认证
```

**成功响应** (200):
```json
{
  "success": true,
  "user_id": 1,
  "username": "john_doe",
  "token": 500
}
```

**cURL 示例**:
```bash
curl -X GET http://localhost:8000/api/users/token/ \
  -b cookies.txt
```

---

## 2. 设置 Token 余额

直接设置用户的 token 值（通常由后端管理系统调用）。

**请求**
```http
POST /api/users/token/update/
Authorization: 需要认证
Content-Type: application/json
```

**请求体**:
```json
{
  "token": 1000
}
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "Token 已更新",
  "user_id": 1,
  "username": "john_doe",
  "old_token": 500,
  "new_token": 1000
}
```

**错误响应** (400):
```json
{
  "success": false,
  "errors": {
    "token": ["Token 不能为负数"]
  }
}
```

---

## 3. 增加 Token

增加用户的 token 余额（用于奖励、充值等）。

**请求**
```http
POST /api/users/token/add/
Authorization: 需要认证
Content-Type: application/json
```

**请求体**:
```json
{
  "amount": 100
}
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "Token 已增加 100",
  "user_id": 1,
  "username": "john_doe",
  "old_token": 500,
  "new_token": 600,
  "amount_changed": 100
}
```

**参数说明**:
| 参数 | 类型 | 说明 |
|------|------|------|
| amount | integer | 增加数额（正整数） |

---

## 4. 扣除 Token

扣除用户的 token 余额（用于支付、扣费等）。

**请求**
```http
POST /api/users/token/deduct/
Authorization: 需要认证
Content-Type: application/json
```

**请求体**:
```json
{
  "amount": 50
}
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "Token 已扣除 50",
  "user_id": 1,
  "username": "john_doe",
  "old_token": 600,
  "new_token": 550,
  "amount_changed": -50
}
```

**错误响应 - 余额不足** (400):
```json
{
  "success": false,
  "message": "Token 余额不足，无法扣除"
}
```

**参数说明**:
| 参数 | 类型 | 说明 |
|------|------|------|
| amount | integer | 扣除数额（正整数）|

**cURL 示例**:
```bash
curl -X POST http://localhost:8000/api/users/token/add/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"amount": 100}'
```

---

# 歌曲管理 API

**基础 URL**: `/api/songs/`  
**功能**: 歌曲上传、管理、浏览

### 核心特性

✓ 每个用户仅能上传一首歌曲  
✓ 音频文件支持 10MB 以内  
✓ 支持的音频格式：mp3, wav, flac, m4a, aac, ogg  
✓ 可选封面图片（2MB 以内）：jpg, png, gif  
✓ 自动去重：SHA256 哈希识别  
✓ 文件自动管理：删除时清理文件  

## 1. 上传歌曲

上传新歌曲。一个用户仅能上传一首歌曲。

**请求**
```http
POST /api/songs/
Authorization: 需要认证
Content-Type: multipart/form-data
```

**参数**:
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| title | string | ✅ | 歌曲标题（1-100 字符）|
| audio_file | file | ✅ | 音频文件，≤10MB |
| cover_image | file | ❌ | 封面图片，≤2MB |
| netease_url | string | ❌ | 网易音乐链接 |

**成功响应** (201 Created):
```json
{
  "success": true,
  "message": "歌曲上传成功",
  "song": {
    "id": 1,
    "title": "My Song",
    "audio_url": "http://localhost:8000/media/songs/audio_user1_song1.mp3",
    "cover_url": "http://localhost:8000/media/songs/cover_user1_song1.jpg",
    "netease_url": "https://music.163.com/song/...",
    "created_at": "2026-01-16T10:30:00Z",
    "updated_at": "2026-01-16T10:30:00Z"
  }
}
```

**错误响应 - 已上传过歌曲** (400):
```json
{
  "success": false,
  "message": "您已上传过歌曲，如需更新请先删除后重新上传",
  "existing_song": {
    "id": 1,
    "title": "My Song",
    "created_at": "2026-01-16T10:30:00Z"
  }
}
```

**错误响应 - 文件过大** (400):
```json
{
  "success": false,
  "errors": {
    "audio_file": ["音频文件不能超过 10MB"]
  }
}
```

**cURL 示例**:
```bash
curl -X POST http://localhost:8000/api/songs/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -b cookies.txt \
  -F "title=My Song" \
  -F "audio_file=@song.mp3" \
  -F "cover_image=@cover.jpg" \
  -F "netease_url=https://music.163.com/song/..."
```

---

## 2. 获取用户的歌曲

获取当前登录用户上传的歌曲。

**请求**
```http
GET /api/songs/me/
Authorization: 需要认证
```

**成功响应** (200):
```json
{
  "success": true,
  "song": {
    "id": 1,
    "title": "My Song",
    "audio_url": "http://localhost:8000/media/songs/audio_user1_song1.mp3",
    "cover_url": "http://localhost:8000/media/songs/cover_user1_song1.jpg",
    "netease_url": "https://music.163.com/song/...",
    "created_at": "2026-01-16T10:30:00Z",
    "updated_at": "2026-01-16T10:30:00Z"
  }
}
```

**错误响应 - 未上传歌曲** (404):
```json
{
  "success": false,
  "message": "您尚未上传过歌曲"
}
```

---

## 3. 更新歌曲信息

更新歌曲的标题和网易链接（不能修改音频文件）。

**请求**
```http
PUT /api/songs/me/
Authorization: 需要认证
Content-Type: application/json
```

**请求体**:
```json
{
  "title": "Updated Song Title",
  "netease_url": "https://music.163.com/song/..."
}
```

**可修改字段**:
- `title` - 歌曲标题
- `netease_url` - 网易音乐链接

**成功响应** (200):
```json
{
  "success": true,
  "message": "歌曲信息已更新",
  "song": {
    "id": 1,
    "title": "Updated Song Title",
    "audio_url": "http://localhost:8000/media/songs/audio_user1_song1.mp3",
    "cover_url": "http://localhost:8000/media/songs/cover_user1_song1.jpg",
    "netease_url": "https://music.163.com/song/...",
    "created_at": "2026-01-16T10:30:00Z",
    "updated_at": "2026-01-16T10:35:00Z"
  }
}
```

---

## 4. 删除歌曲

删除当前用户的歌曲（同时删除对应的文件）。

**请求**
```http
DELETE /api/songs/me/
Authorization: 需要认证
```

**成功响应** (200):
```json
{
  "success": true,
  "message": "歌曲已删除",
  "deleted_song": {
    "id": 1,
    "title": "My Song"
  }
}
```

---

## 5. 列出所有歌曲

获取所有用户的歌曲列表（支持分页）。

**请求**
```http
GET /api/songs/?page=1&page_size=10
Authorization: 不需要
```

**查询参数**:
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码 |
| page_size | integer | 10 | 每页数量 |

**成功响应** (200):
```json
{
  "success": true,
  "count": 25,
  "page": 1,
  "page_size": 10,
  "total_pages": 3,
  "results": [
    {
      "id": 1,
      "title": "Song 1",
      "user": {
        "id": 1,
        "username": "user1"
      },
      "audio_url": "http://localhost:8000/media/songs/audio_user1_song1.mp3",
      "created_at": "2026-01-16T10:30:00Z"
    },
    {
      "id": 2,
      "title": "Song 2",
      "user": {
        "id": 2,
        "username": "user2"
      },
      "audio_url": "http://localhost:8000/media/songs/audio_user2_song2.mp3",
      "created_at": "2026-01-16T11:00:00Z"
    }
  ]
}
```

---

## 6. 获取特定歌曲详情

获取指定歌曲的完整信息。

**请求**
```http
GET /api/songs/{id}/
Authorization: 不需要
```

**URL 参数**:
| 参数 | 类型 | 说明 |
|------|------|------|
| id | integer | 歌曲 ID |

**成功响应** (200):
```json
{
  "success": true,
  "song": {
    "id": 1,
    "title": "My Song",
    "user": {
      "id": 1,
      "username": "user1"
    },
    "audio_url": "http://localhost:8000/media/songs/audio_user1_song1.mp3",
    "cover_url": "http://localhost:8000/media/songs/cover_user1_song1.jpg",
    "netease_url": "https://music.163.com/song/...",
    "created_at": "2026-01-16T10:30:00Z",
    "updated_at": "2026-01-16T10:30:00Z"
  }
}
```

**错误响应 - 歌曲不存在** (404):
```json
{
  "detail": "Not found."
}
```

---

## 文件管理

### 文件命名规则

上传的文件会按照以下规则重命名：

```
音频文件: audio_user{user_id}_song{song_id}.{ext}
封面图片: cover_user{user_id}_song{song_id}.{ext}
```

**示例**:
- 用户 ID 为 1 的音频文件：`audio_user1_song1.mp3`
- 用户 ID 为 2 的封面图片：`cover_user2_song2.jpg`

### 支持的文件格式

**音频文件**:
- mp3, wav, flac, m4a, aac, ogg

**图片文件**:
- jpg, jpeg, png, gif

### 文件大小限制

- 音频文件：≤ 10MB
- 封面图片：≤ 2MB
- 单次请求：≤ 10MB

### 去重机制

系统使用 SHA256 哈希来识别重复音频文件：

1. 上传时，系统计算音频文件的 SHA256 哈希
2. 存储用户信息和文件
3. 不同用户可以上传相同的音频文件（哈希相同）
4. 系统能够识别哪些用户上传了相同的音频

---

# 错误处理

## 状态码

| 状态码 | 说明 | 常见原因 |
|--------|------|--------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 参数错误、验证失败 |
| 401 | Unauthorized | 未认证或认证失败 |
| 403 | Forbidden | 权限不足、CSRF 验证失败 |
| 404 | Not Found | 资源不存在 |
| 413 | Payload Too Large | 文件过大 |
| 500 | Server Error | 服务器错误 |

## 错误响应示例

**参数验证错误**:
```json
{
  "success": false,
  "errors": {
    "username": ["用户名已存在"],
    "email": ["邮箱格式不正确"]
  }
}
```

**认证错误**:
```json
{
  "success": false,
  "message": "用户名或密码错误"
}
```

**权限错误**:
```json
{
  "success": false,
  "message": "您没有权限进行此操作"
}
```

**文件错误**:
```json
{
  "success": false,
  "errors": {
    "audio_file": ["文件大小不能超过 10MB"]
  }
}
```

---

# 安全特性

## 1. 密码安全

- ✅ 最小长度 8 个字符
- ✅ 密码强度验证（必须包含字母和数字）
- ✅ 使用 Django 的 Argon2 哈希算法
- ✅ 密码验证时进行 timing attack 防护

## 2. CSRF 保护

- ✅ 所有 POST/PUT/DELETE 请求都需要 CSRF Token
- ✅ CSRF Token 在 Cookie 中自动设置
- ✅ 前端框架（如 axios）会自动从 Cookie 读取并在请求头中发送

## 3. 会话认证

- ✅ 使用 Django Session 管理用户认证状态
- ✅ Session ID 存储在 Cookie 中（HTTPOnly）
- ✅ 支持 CORS 跨域请求
- ✅ 支持多设备同时登录

## 4. 数据验证

- ✅ 邮箱唯一性检查
- ✅ 用户名唯一性检查
- ✅ 文件格式和大小验证
- ✅ 输入类型和长度验证

## 5. 文件安全

- ✅ 文件扩展名白名单验证
- ✅ MIME 类型检查
- ✅ 文件大小限制
- ✅ 自动文件清理

## 6. 速率限制

建议在生产环境中配置速率限制，防止滥用。

---

# 前端集成

## JavaScript / TypeScript

### 1. 安装 Axios

```bash
npm install axios
```

### 2. 创建 API 服务

```javascript
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // 重要：允许跨域请求携带 Cookie
  headers: {
    'Content-Type': 'application/json',
  },
});

// 自动从 Cookie 读取 CSRF Token
api.interceptors.request.use((config) => {
  const csrftoken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  
  if (csrftoken) {
    config.headers['X-CSRFToken'] = csrftoken;
  }
  
  return config;
});

export default api;
```

### 3. 用户认证服务

```javascript
import api from './api';

export const authService = {
  register: (data) => api.post('/users/register/', data),
  login: (data) => api.post('/users/login/', data),
  logout: () => api.post('/users/logout/'),
  getCurrentUser: () => api.get('/users/me/'),
  updateProfile: (data) => api.put('/users/profile/', data),
  changePassword: (data) => api.post('/users/change-password/', data),
  checkUsername: (username) => api.post('/users/check-username/', { username }),
  checkEmail: (email) => api.post('/users/check-email/', { email }),
};
```

### 4. Token 服务

```javascript
export const tokenService = {
  getBalance: () => api.get('/users/token/'),
  updateToken: (amount) => api.post('/users/token/update/', { token: amount }),
  addToken: (amount) => api.post('/users/token/add/', { amount }),
  deductToken: (amount) => api.post('/users/token/deduct/', { amount }),
};
```

### 5. 歌曲服务

```javascript
export const songService = {
  upload: (formData) => api.post('/songs/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
  getMyS: () => api.get('/songs/me/'),
  updateSong: (data) => api.put('/songs/me/', data),
  deleteSong: () => api.delete('/songs/me/'),
  getSongs: (page = 1, pageSize = 10) => 
    api.get('/songs/', { params: { page, page_size: pageSize } }),
  getSongDetail: (id) => api.get(`/songs/${id}/`),
};
```

### 6. 使用示例

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
  console.log('登录成功:', response.data.user);
} catch (error) {
  console.error('登录失败:', error.response.data);
}

// 上传歌曲
try {
  const formData = new FormData();
  formData.append('title', 'My Song');
  formData.append('audio_file', audioFile); // File object
  formData.append('cover_image', coverImage); // File object
  formData.append('netease_url', 'https://music.163.com/...');
  
  const response = await songService.upload(formData);
  console.log('上传成功:', response.data);
} catch (error) {
  console.error('上传失败:', error.response.data);
}
```

---

## Vue 3 示例

### 使用 Pinia 管理状态

```typescript
// stores/auth.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';
import authService from '@/services/auth';

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null);
  const isLoading = ref(false);

  const login = async (username, password) => {
    isLoading.value = true;
    try {
      const response = await authService.login({ username, password });
      user.value = response.data.user;
      return response.data;
    } finally {
      isLoading.value = false;
    }
  };

  const logout = async () => {
    await authService.logout();
    user.value = null;
  };

  return { user, isLoading, login, logout };
});
```

### Vue 组件

```vue
<template>
  <div>
    <input v-model="form.username" placeholder="用户名" />
    <input v-model="form.password" type="password" placeholder="密码" />
    <button @click="handleLogin" :disabled="isLoading">
      {{ isLoading ? '登录中...' : '登录' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();
const form = ref({ username: '', password: '' });
const isLoading = ref(false);

const handleLogin = async () => {
  try {
    isLoading.value = true;
    await authStore.login(form.value.username, form.value.password);
    // 登录成功后的操作
  } catch (error) {
    console.error('登录失败:', error);
  } finally {
    isLoading.value = false;
  }
};
</script>
```

---

# 常见问题

## Q1: 如何处理 CSRF Token？

**A**: CSRF Token 会自动在 Cookie 中设置为 `csrftoken`。大多数 HTTP 客户端库（如 axios）会自动从 Cookie 中读取并在请求头 `X-CSRFToken` 中发送。

## Q2: 会话会过期吗？

**A**: 是的。Django 默认的会话过期时间是 14 天。可以在 settings.py 中修改 `SESSION_COOKIE_AGE` 来调整。

## Q3: 如何在 Vue 中持久化用户登录状态？

**A**: 建议在应用启动时调用 `/api/users/me/` 端点来验证用户是否已登录。如果返回 200，则用户已登录；如果返回 401，则需要重新登录。

## Q4: 能否从多个设备同时登录？

**A**: 可以。每个设备都会获得独立的 Session ID，这些会话互不影响。

## Q5: 忘记密码怎么办？

**A**: 当前版本不支持密码重置功能。在生产环境中应该实现邮箱验证的密码重置功能。

## Q6: 一个用户真的只能上传一首歌曲吗？

**A**: 是的。这是系统设计的核心特性，由 `Song` 模型中的 `OneToOneField` 强制实现。删除旧歌曲后才能上传新歌曲。

## Q7: 上传的文件会被保存到哪里？

**A**: 文件会被保存到 `backend/xmmcg/media/songs/` 目录下。文件名会按照 `audio_user{user_id}_song{song_id}.{ext}` 的格式重命名。

## Q8: 如何下载用户上传的文件？

**A**: 在开发环境中，文件通过 Django 的静态文件服务直接提供。API 响应中的 `audio_url` 和 `cover_url` 是完整的可访问 URL。生产环境建议使用 CDN。

## Q9: Token 可以为负数吗？

**A**: 不可以。系统会验证 Token 不能为负数。扣除时，如果 Token 余额不足，会返回错误。

## Q10: 支持哪些音频格式？

**A**: 支持 mp3, wav, flac, m4a, aac, ogg 等常见格式。任何其他格式都会被拒绝。

---

## 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | Django | 6.0.1 |
| API | Django REST Framework | 3.14.0 |
| 跨域 | django-cors-headers | 4.3.1 |
| 认证 | Django Session | 内置 |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | - |
| 密码 | Argon2 | 内置 |
| 文件处理 | Pillow | - |

---

## 部署检查清单

- [ ] 环境变量配置完毕
- [ ] DEBUG = False
- [ ] SECRET_KEY 已更改
- [ ] ALLOWED_HOSTS 已配置
- [ ] 数据库迁移已应用
- [ ] 静态文件已收集
- [ ] CORS 设置已调整
- [ ] HTTPS 已启用
- [ ] 备份策略已制定
- [ ] 日志监控已启用

---

**最后更新**: 2026-01-16  
**维护者**: XMMCG 开发团队  
**许可证**: MIT
