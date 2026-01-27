# XMMCG 部署指南

完整的 Google Compute Engine 部署文档，包括初始部署、代码更新、故障排查等。

---

## 📋 目录

1. [系统要求](#系统要求)
2. [初始部署](#初始部署)
3. [配置说明](#配置说明)
4. [代码更新](#代码更新)
5. [服务管理](#服务管理)
6. [故障排查](#故障排查)
7. [备份恢复](#备份恢复)

---

## 🖥️ 系统要求

### 推荐配置

- **操作系统**: Debian 11/12 或 Ubuntu 22.04 LTS
- **CPU**: 2 核心
- **内存**: 2 GB
- **磁盘**: 20 GB
- **网络**: 公网 IP，开放 80 和 443 端口

### 创建 GCP 实例

```bash
gcloud compute instances create xmmcg-server \
    --machine-type=e2-small \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --boot-disk-size=20GB \
    --tags=http-server,https-server
```

---

## 🚀 初始部署

### 步骤 1: SSH 连接到服务器

```bash
gcloud compute ssh xmmcg-server
```

或使用标准 SSH：
```bash
ssh user@your-server-ip
```

### 步骤 2: 克隆项目

```bash
# 克隆代码仓库
git clone https://github.com/yukunf/xmmcg-net.git
cd xmmcg-net
```

### 步骤 3: 运行部署脚本

```bash
# 执行一键部署脚本
sudo bash deploy.sh
```

部署脚本会自动完成：
- ✅ 安装系统依赖（Python, Node.js, Nginx, Certbot）
- ✅ 创建 Python 虚拟环境
- ✅ 安装 Python 和 Node.js 依赖
- ✅ 构建前端应用
- ✅ 数据库迁移
- ✅ 收集静态文件
- ✅ 配置并启动 Gunicorn 和 Nginx

### 步骤 4: 配置环境变量

```bash
sudo nano /opt/xmmcg/.env
```

**重要配置项**：

```env
# Django 核心设置
SECRET_KEY=生成的随机密钥  # 由部署脚本自动生成
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip

# 生产域名
PRODUCTION_DOMAIN=your-domain.com

# Majdata.net API 配置（谱面自动上传功能）
ENABLE_CHART_FORWARD_TO_MAJDATA=True  # 是否启用自动上传到 Majdata
MAJDATA_USERNAME=xmmcg5  # Majdata 账号用户名
MAJDATA_PASSWD_HASHED=your-password-hash  # Majdata 密码哈希值
MAJDATA_BASE_URL=https://majdata.net/api3/api/  # 可选，默认值已配置
MAJDATA_LOGIN_URL=https://majdata.net/api3/api/account/Login  # 可选
MAJDATA_UPLOAD_URL=https://majdata.net/api3/api/maichart/upload  # 可选

# 互评系统配置
PEER_REVIEW_TASKS_PER_USER=8  # 每个用户需要完成的评分任务数
PEER_REVIEW_MAX_SCORE=50  # 互评满分
```

**Majdata 登录配置说明**：

1. **密码哈希值获取方法**：
   ```bash
   # 方法1: 使用 Python 计算 MD5 哈希
   echo -n "your-password" | md5sum
   
   # 方法2: 使用 Python 脚本
   python3 -c "import hashlib; print(hashlib.md5('your-password'.encode()).hexdigest())"
   ```

2. **完整配置示例**：
   ```env
   MAJDATA_USERNAME=xmmcg5
   MAJDATA_PASSWD_HASHED=5f4dcc3b5aa765d61d8327deb882cf99  # 示例哈希
   ```

3. **禁用 Majdata 自动上传**：
   ```env
   ENABLE_CHART_FORWARD_TO_MAJDATA=False
   ```

4. **配置优先级**：
   - 环境变量（.env 文件）> settings.py 默认值
   - 所有 Majdata 配置均可在 `/opt/xmmcg/.env` 中修改
   - 无需修改代码即可更换账号

修改后重启服务：
```bash
sudo systemctl restart gunicorn
```

### 步骤 5: 创建管理员账号

```bash
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py createsuperuser
```

### 步骤 6: 配置防火墙

**GCP 控制台配置**（推荐）：
1. 进入 VPC 网络 > 防火墙
2. 确保有规则允许 TCP:80 和 TCP:443

**或使用命令行**：
```bash
gcloud compute firewall-rules create allow-http --allow tcp:80
gcloud compute firewall-rules create allow-https --allow tcp:443
```

### 步骤 7: 配置 SSL 证书（可选）

**前提**：域名已解析到服务器 IP

```bash
# 检查域名解析
nslookup your-domain.com

# 申请免费 SSL 证书
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 测试自动续期
sudo certbot renew --dry-run
```

---

## ⚙️ 配置说明

### 目录结构

```
/opt/xmmcg/                    # 项目根目录
├── backend/xmmcg/             # Django 后端
│   ├── db.sqlite3             # SQLite 数据库
│   ├── manage.py              # Django 管理命令
│   └── media/                 # 用户上传文件（临时）
├── front/                     # Vue 前端源码
├── venv/                      # Python 虚拟环境
├── .env                       # 环境变量配置
├── deploy.sh                  # 初始部署脚本
└── update.sh                  # 代码更新脚本

/var/www/xmmcg/                # 静态文件部署目录
├── static/                    # Django 静态文件
├── media/                     # 用户上传文件
└── frontend/                  # Vue 构建后的前端

/etc/nginx/sites-available/    # Nginx 配置
└── xmmcg                      # 项目 Nginx 配置文件

/etc/systemd/system/           # Systemd 服务
└── gunicorn.service           # Gunicorn 服务配置
```

### 环境变量详解

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `SECRET_KEY` | Django 加密密钥 | 自动生成 | ✅ |
| `DEBUG` | 调试模式 | `False` | ✅ |
| `ALLOWED_HOSTS` | 允许访问的主机名 | `*` | ✅ |
| `PRODUCTION_DOMAIN` | 生产环境域名 | - | ✅ |
| `ENABLE_CHART_FORWARD_TO_MAJDATA` | 是否启用 Majdata 自动上传 | `True` | ❌ |
| `MAJDATA_USERNAME` | Majdata 账号用户名 | `xmmcg5` | ⚠️ |
| `MAJDATA_PASSWD_HASHED` | Majdata 密码哈希（MD5） | - | ⚠️ |
| `MAJDATA_BASE_URL` | Majdata API 基础 URL | 已配置 | ❌ |
| `MAJDATA_LOGIN_URL` | Majdata 登录 API | 已配置 | ❌ |
| `MAJDATA_UPLOAD_URL` | Majdata 上传 API | 已配置 | ❌ |
| `PEER_REVIEW_TASKS_PER_USER` | 互评任务数 | `8` | ❌ |
| `PEER_REVIEW_MAX_SCORE` | 互评满分 | `50` | ❌ |

**图例**: ✅ 必须配置 | ⚠️ 启用 Majdata 时必须 | ❌ 可选（有默认值）

---

## 🔄 代码更新

### 自动更新（推荐）

```bash
# 运行更新脚本
sudo bash /opt/xmmcg/update.sh
```

更新脚本会自动：
1. ✅ 拉取最新代码
2. ✅ 更新 Python 依赖
3. ✅ 应用数据库迁移
4. ✅ 重新构建前端
5. ✅ 收集静态文件
6. ✅ 重启服务

### 手动更新步骤

```bash
# 1. 拉取代码
cd /opt/xmmcg
git pull

# 2. 更新后端
source /opt/xmmcg/venv/bin/activate
pip install -r backend/xmmcg/requirements.txt
cd backend/xmmcg
python manage.py migrate
python manage.py collectstatic --noinput

# 3. 更新前端
cd /opt/xmmcg/front
npm install
npm run build
sudo cp -r dist/* /var/www/xmmcg/frontend/

# 4. 重启服务
sudo systemctl restart gunicorn
sudo systemctl reload nginx
```

### 仅更新前端

```bash
cd /opt/xmmcg/front
git pull
npm install
npm run build
sudo cp -r dist/* /var/www/xmmcg/frontend/
```

### 仅更新后端

```bash
cd /opt/xmmcg
git pull
source venv/bin/activate
cd backend/xmmcg
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

---

## 🛠️ 服务管理

### Gunicorn (Django 应用)

```bash
# 查看状态
sudo systemctl status gunicorn

# 启动/停止/重启
sudo systemctl start gunicorn
sudo systemctl stop gunicorn
sudo systemctl restart gunicorn

# 查看实时日志
sudo journalctl -u gunicorn -f

# 查看最近 50 条日志
sudo journalctl -u gunicorn -n 50
```

### Nginx (Web 服务器)

```bash
# 查看状态
sudo systemctl status nginx

# 启动/停止/重启
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx

# 重新加载配置（不中断服务）
sudo systemctl reload nginx

# 测试配置文件
sudo nginx -t

# 查看错误日志
sudo tail -f /var/log/nginx/xmmcg_error.log

# 查看访问日志
sudo tail -f /var/log/nginx/xmmcg_access.log
```

### 服务开机自启

```bash
# 启用开机自启（已自动配置）
sudo systemctl enable gunicorn
sudo systemctl enable nginx

# 禁用开机自启
sudo systemctl disable gunicorn
sudo systemctl disable nginx

# 检查是否启用
sudo systemctl is-enabled gunicorn
sudo systemctl is-enabled nginx
```

---

## 🐛 故障排查

### 常见问题速查

#### 问题 1: API 返回 400 Bad Request

**症状**: 浏览器访问 API 返回 `Bad Request (400)`

**原因**: 域名未在 `ALLOWED_HOSTS` 或 `CSRF_TRUSTED_ORIGINS` 中配置

**解决方案**:
```bash
# 编辑 .env 文件
sudo nano /opt/xmmcg/.env
```

添加以下配置（替换为你的域名）:
```env
ALLOWED_HOSTS=xmmcg.majdata.net,149.104.29.136,localhost
CSRF_TRUSTED_ORIGINS=https://xmmcg.majdata.net,https://149.104.29.136
PRODUCTION_DOMAIN=xmmcg.majdata.net
```

重启服务:
```bash
sudo systemctl restart gunicorn
```

验证配置:
```bash
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py shell -c "from django.conf import settings; print(settings.ALLOWED_HOSTS)"
```

---

### 问题 2: 数据库表缺失 (OperationalError: no such table)
现象：


访问特定 App 的页面（如 /admin/songs/banner/）时报错 500。

**错误**：开启 Debug 模式后看到具体报错：`OperationalError: no such table: songs_banner`。

运行 python manage.py migrate 提示 "No migrations to apply"，但数据库里确实没表。

**原因**:


migrate 命令**只负责执行已存在的迁移文件。如果新创建了 Model 但没有生成迁移文件（Blueprint），Django 不会自动创建表。**这通常发生在新建 App 或新加 Model 后忘记执行 makemigrations。

**解决方案**:


必须先生成迁移文件，再执行迁移。

检查配置：确保新 App 已加入 settings.py 的 INSTALLED_APPS 中。

**强制生成迁移：指定 App 名称生成迁移文件。例如：`python3 manage.py makemigration songs`**

应用迁移。

Bash
cd /opt/xmmcg/backend
source /opt/xmmcg/venv/bin/activate

#### 步骤 1: 生成图纸 (必须指定 App 名字，例如 songs)
python manage.py makemigrations songs
python manage.py makemigrations users
python manage.py makemigrations

#### 步骤 2: 开始施工
python manage.py migrate
#### 步骤 3: 重启服务
sudo systemctl restart gunicorn

---

### 3. 管理员账户登录失败 (Invalid Password / Hash Mismatch)

#### 现象
* 使用 `createsuperuser` 创建的账户无法登录 Admin，提示密码错误。
* 或者创建时报错哈希算法相关错误。

#### 原因
在命令行直接运行 `createsuperuser` 时，如果未正确加载环境变量（`.env`），Django 可能会使用默认或空的 `SECRET_KEY` 进行密码哈希。而 Gunicorn 运行时加载了正确的 `.env`，导致两边的哈希“盐”不一致，密码无法匹配。

#### 解决方案
使用 Python 脚本，在加载了完整 Django 环境和环境变量的上下文中重置密码。

**操作步骤：**

1. 创建脚本 `ensure_admin.py`：

```python
import os, sys, django
sys.path.append('/opt/xmmcg/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
u, _ = User.objects.get_or_create(username='admin')
u.set_password('你的强密码')  # 这里会使用正确的 SECRET_KEY 进行哈希
u.is_superuser = True
u.is_staff = True
u.save()
print("✅ Password reset successfully.")
```

2. **关键：带环境变量执行脚本**：

```bash
cd /opt/xmmcg/backend
# 导出 .env 变量 -> 激活环境 -> 运行脚本
set -a; source /opt/xmmcg/.env; set +a; /opt/xmmcg/venv/bin/python ensure_admin.py
```

---

### 4. 常用调试命令速查表

当遇到未知 500 错误时，按以下顺序操作：

**1. 查看实时错误日志 (最有效)**
```bash
# 能够看到具体的 Python Traceback
sudo tail -f -n 50 /var/log/gunicorn/error.log
```

**2. 临时开启 Debug 模式**
如果日志看不清，可以临时让页面显示报错黄页。
* 修改 `.env`: `DEBUG=True`
* 重启: `sudo systemctl restart gunicorn`
* **注意**: 调试完必须改回 `False`！

**3. 检查 Nginx 转发**
```bash
sudo tail -f -n 50 /var/log/nginx/xmmcg_error.log
```

**4. 检查服务状态**
```bash
sudo systemctl status gunicorn
sudo systemctl status nginx
```

---

#### 问题 3: 数据库迁移冲突

**症状**: `FieldDoesNotExist` 或 `InconsistentMigrationHistory`

**原因**: 服务器上存在本地生成的迁移文件与仓库不一致

**解决方案**:
```bash
cd /opt/xmmcg
git pull origin main

# 删除本地生成的迁移（0008 之后）
rm -f backend/xmmcg/songs/migrations/0008_*.py
rm -f backend/xmmcg/songs/migrations/0009_*.py
find backend/xmmcg/songs/migrations/ -name "*.pyc" -delete

# 重新运行迁移
cd backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py migrate
```

开发环境重置（⚠️ 会丢失数据）:
```bash
cd /opt/xmmcg/backend/xmmcg
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
python manage.py add_sample_data
```

---

#### 问题 4: Admin 无法登录

**原因**: 超级用户未创建或密码错误

**创建超级用户**:
```bash
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py createsuperuser
```

**重置密码**:
```bash
python manage.py shell
```
```python
from django.contrib.auth.models import User
user = User.objects.get(username='admin')
user.set_password('new_password')
user.save()
exit()
```

---

#### 问题 5: 502 Bad Gateway


#### 又一种可能性 

**原因**：修改migrate之后**gunicron又失去了权限。**

##### 解决办法

先把如下的权限刷给他。

```
# 1. 修复后端代码 & SQLite 权限 (核心)
chown -R www-data:www-data /opt/xmmcg/backend

# 2. 修复日志权限 (防止启动失败)
chown -R www-data:www-data /var/log/gunicorn

# 3. 修复上传目录权限 (防止上传报错)
chown -R www-data:www-data /var/www/xmmcg/media

# 4. 修复配置读取权限 (防止读不到 .env)
chown www-data:www-data /opt/xmmcg/.env
chmod 640 /opt/xmmcg/.env

# 5. 重启服务生效
systemctl restart gunicorn
```


使其可以重启后自动解决run目录问题。执行`vim /etc/systemd/system/gunicorn.service`，向里面添加
```bash
[Service]
# ... 其他配置 ...
User=www-data
Group=www-data

# ✅ 核心配置：这行指令告诉 Systemd：
# "在启动服务前，请在 /run/ 下创建一个叫 gunicorn 的目录，
# 并把它所有权给 User 设置的用户 (www-data)。
# 服务停止时，自动删掉这个目录。"
RuntimeDirectory=gunicorn

# 你的 Socket 绑定路径 (必须匹配上面的目录)
# 注意：这里路径不用改，RuntimeDirectory=gunicorn 会自动对应 /run/gunicorn/
ExecStart=/opt/xmmcg/venv/bin/gunicorn \
    --bind unix:/run/gunicorn/xmmcg.sock \
    # ... 其他参数 ...
```


然后执行

```bash
# 1. 告诉 Systemd 读取新配置
systemctl daemon-reload

# 2. 重启服务
systemctl restart gunicorn

# 3. 验证目录是否自动创建
ls -ld /run/gunicorn
```

---
**原因**: Gunicorn 未运行或 socket 文件问题

**解决**:
```bash
# 检查 Gunicorn 状态
sudo systemctl status gunicorn

# 检查 socket 文件
ls -l /var/run/gunicorn/xmmcg.sock

# 重启 Gunicorn
sudo systemctl restart gunicorn

# 查看详细错误
sudo journalctl -u gunicorn -xe
```

#### 问题 6: 静态文件 404

**原因**: 静态文件未收集或路径错误

**解决**:
```bash
# 重新收集静态文件
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py collectstatic --noinput

# 检查权限
sudo chown -R www-data:www-data /var/www/xmmcg/static/

# 测试访问
curl http://localhost/static/admin/css/base.css
```

---

#### 问题 7: 文件上传失败

**原因**: media 目录权限问题

**解决**:
```bash
# 设置正确权限
sudo chown -R www-data:www-data /var/www/xmmcg/media/
sudo chmod -R 755 /var/www/xmmcg/media/

# 检查 Nginx 上传大小限制
sudo nano /etc/nginx/sites-available/xmmcg
# 确保有: client_max_body_size 25M;

sudo systemctl reload nginx
```

---

#### 问题 8: HTTPS 证书警告（使用 IP 访问）

**症状**: 浏览器显示 "不安全连接" 或 SSL 证书错误

**原因**: SSL 证书不能颁发给 IP 地址，只能颁发给域名

**临时方案**:
- 使用 HTTP: `http://149.104.29.136`
- 浏览器点击"高级" → "继续访问"（仅测试）

**正确方案**:
1. 配置域名并添加 DNS A 记录
2. 安装 SSL 证书:
```bash
sudo certbot --nginx -d your-domain.com
```
3. 更新 .env:
```env
DEBUG=False
PRODUCTION_DOMAIN=your-domain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

#### 问题 9: 数据库只读错误

**症状**: Admin 登录时报错 `attempt to write a readonly database`

**原因**: SQLite 数据库文件或包含数据库的目录权限不正确。SQLite 需要：
1. 对 `db.sqlite3` 文件有读写权限
2. 对包含数据库的**目录**也要有写权限（用于创建临时文件）

**解决方案**:
```bash
cd /opt/xmmcg/backend/xmmcg

# 修复数据库文件权限
sudo chown www-data:www-data db.sqlite3
sudo chmod 664 db.sqlite3

# 修复目录权限（重要！）
sudo chown www-data:www-data .
sudo chmod 775 .

# 重启服务
sudo systemctl restart gunicorn
```

---

#### 问题 10: CORS 错误

**原因**: 前端域名未添加到白名单

**解决**:
```bash
# 编辑环境变量
sudo nano /opt/xmmcg/.env

# 设置正确的域名
PRODUCTION_DOMAIN=your-domain.com

# 重启 Gunicorn
sudo systemctl restart gunicorn
```

---

#### 问题 11: Git 权限错误

**错误**: `fatal: detected dubious ownership`

**解决**:
```bash
git config --global --add safe.directory /opt/xmmcg
```

#### 问题11：下载文件带CORS导致ERR 200 OK
**错误** : `ERROR 200 (OK)`
**解决**：服务器上媒体映射到`/var/www/media/...`，获得`/media`开始的路径应该直接拿相对路径向nginx请求。

修复代码：

```python
const resolveUrl = (url) => {
  if (!url) return null

  // 1. 如果已经是完整的绝对路径（比如外链），直接返回，不动它
  if (url.startsWith('http://') || url.startsWith('https://')) return url

  // 2. 判断当前是否在开发环境
  // 通常开发环境 hostname 是 localhost 或 127.0.0.1
  const isDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'

  if (isDev) {
    // === 开发环境 ===
    // 必须拼接后端地址，否则请求会发给前端开发服务器 (如 port 5173)
    // 这里默认后端是 8000，如果你的 window.API_BASE_URL 没设置，就会用这个兜底
    const apiBase = window.API_BASE_URL || `${window.location.protocol}//${window.location.hostname}:8000`
    try {
      return new URL(url, apiBase).href
    } catch (e) {
      return `${apiBase}${url}`
    }
  } else {
    // === 生产/远程环境 ===
    // 返回相对路径 (如 "/media/songs/xxx.mp3")
    // 浏览器会自动把它当作 https://xmmcg.majdata.net/media/...
    // 【关键】同源请求不触发 CORS 检查！
    return url.startsWith('/') ? url : `/${url}`
  }
}
```


---

### 日志查看命令

```bash
# Gunicorn 日志
sudo journalctl -u gunicorn -n 50
sudo journalctl -u gunicorn -f  # 实时查看

# Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# 检查服务状态
sudo systemctl status gunicorn nginx
```

---

## 💾 备份恢复

### 数据库备份

```bash
# 手动备份
sudo cp /opt/xmmcg/backend/xmmcg/db.sqlite3 \
        /opt/xmmcg/backup_$(date +%Y%m%d_%H%M%S).sqlite3

# 定期自动备份（添加到 crontab）
sudo crontab -e
# 添加: 0 2 * * * cp /opt/xmmcg/backend/xmmcg/db.sqlite3 /opt/xmmcg/backup_$(date +\%Y\%m\%d).sqlite3
```

### 媒体文件备份

```bash
# 打包备份
sudo tar -czf /opt/xmmcg/media_backup_$(date +%Y%m%d).tar.gz \
              /var/www/xmmcg/media/

# 恢复备份
sudo tar -xzf /opt/xmmcg/media_backup_20260119.tar.gz -C /
```

### 完整系统备份

```bash
# 备份整个项目
sudo tar -czf /tmp/xmmcg_full_backup_$(date +%Y%m%d).tar.gz \
    /opt/xmmcg \
    /var/www/xmmcg \
    /etc/nginx/sites-available/xmmcg \
    /etc/systemd/system/gunicorn.service

# 下载到本地
gcloud compute scp xmmcg-server:/tmp/xmmcg_full_backup_*.tar.gz ./
```

### 数据恢复

```bash
# 停止服务
sudo systemctl stop gunicorn

# 恢复数据库
sudo cp /opt/xmmcg/backup_20260119.sqlite3 \
        /opt/xmmcg/backend/xmmcg/db.sqlite3

# 重启服务
sudo systemctl start gunicorn
```

---

## 📊 监控和维护

### 磁盘空间监控

```bash
# 检查磁盘使用
df -h

# 检查项目目录大小
du -sh /opt/xmmcg
du -sh /var/www/xmmcg

# 清理日志（保留最近 7 天）
sudo journalctl --vacuum-time=7d
```

### 性能优化

**调整 Gunicorn Workers**:
```bash
# 编辑服务配置
sudo nano /etc/systemd/system/gunicorn.service

# 公式: workers = (2 × CPU核心数) + 1
# 例如 2 核: --workers 5

sudo systemctl daemon-reload
sudo systemctl restart gunicorn
```

**启用 Nginx 缓存**:
```bash
sudo nano /etc/nginx/sites-available/xmmcg

# 在 server 块外添加:
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=my_cache:10m;

# 在 location / 块内添加:
proxy_cache my_cache;
proxy_cache_valid 200 1h;
```

### 安全加固

```bash
# 启用自动安全更新
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades

# 配置防火墙
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# 禁用 root SSH 登录
sudo nano /etc/ssh/sshd_config
# 设置: PermitRootLogin no
sudo systemctl restart sshd
```

---

## 🔗 常用链接

- **服务器访问**: `http://your-server-ip` 或 `https://your-domain.com`
- **管理后台**: `/admin/`
- **API 文档**: `/api/`
- **GitHub 仓库**: https://github.com/yukunf/xmmcg-net

---

## 📞 技术支持

遇到问题请查看：
- 项目文档: `/doc/apidoc/`
- 实现报告: `/doc/Implementation Report/`
- GitHub Issues: https://github.com/yukunf/xmmcg-net/issues

---

**最后更新**: 2026-01-19  
**维护者**: XMMCG Team
