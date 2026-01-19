# 故障排除指南 (Troubleshooting Guide)

## 问题 0: API 返回 500 错误 + HTTPS 不安全连接警告

### 症状
```
GET https://149.104.29.136/api/songs/phases/ 500 (Internal Server Error)
浏览器显示: "不安全连接" 或 SSL 证书错误
```

### 原因分析
1. **使用 IP 地址访问 HTTPS**: 浏览器无法验证 IP 地址的 SSL 证书
2. **CSRF/CORS 配置未包含 IP 地址**: Django 拒绝来自未信任源的请求
3. **数据库未初始化**: CompetitionPhase 表为空导致序列化失败
4. **DEBUG=False 时的严格安全检查**: 生产模式要求更严格的配置

### 解决方案

#### 步骤 1: 在服务器上配置 .env 文件
编辑 `/opt/xmmcg/.env`:
```bash
# 基础配置
DEBUG=True  # 临时启用调试模式查看详细错误
SECRET_KEY=your-random-secret-key-here

# 主机配置 (允许 IP 访问)
ALLOWED_HOSTS=149.104.29.136,localhost,127.0.0.1

# CSRF 信任源 (必须包含 HTTPS IP)
CSRF_TRUSTED_ORIGINS=https://149.104.29.136,http://149.104.29.136

# 如果有域名，也添加进来
# PRODUCTION_DOMAIN=your-domain.com
```

#### 步骤 2: 查看后端详细错误
```bash
# 查看 Gunicorn 日志
sudo journalctl -u gunicorn -n 50

# 或实时监控
sudo journalctl -u gunicorn -f
```

常见错误类型：
- **"Invalid HTTP_HOST header"**: ALLOWED_HOSTS 配置问题
- **"CSRF verification failed"**: CSRF_TRUSTED_ORIGINS 配置问题  
- **"RelatedObjectDoesNotExist"**: 数据库数据缺失
- **"OperationalError"**: 数据库迁移未完成

#### 步骤 3: 初始化数据库数据
```bash
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate

# 运行迁移
python manage.py migrate

# 创建测试数据 (包括 CompetitionPhase)
python manage.py add_sample_data

# 或手动创建超级用户
python manage.py createsuperuser
```

#### 步骤 4: 重启服务
```bash
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

#### 步骤 5: 测试 API
```bash
# 在服务器本地测试
curl http://localhost/api/songs/phases/

# 应该返回 JSON 数据，例如:
# [{"id":1,"name":"选歌阶段","slug":"song_selection",...}]
```

### 关于 HTTPS + IP 地址的说明

**问题**: SSL 证书不能颁发给 IP 地址，只能颁发给域名。

**临时解决方案（开发/测试）**:
1. **使用 HTTP 访问**: `http://149.104.29.136`（不安全但可用）
2. **浏览器忽略证书警告**: 点击"高级" → "继续访问"（仅测试用）

**正确解决方案（生产环境）**:
1. **配置域名**:
   - 购买域名（如 `example.com`）
   - 在 DNS 中添加 A 记录指向 `149.104.29.136`
   
2. **安装 SSL 证书**:
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

3. **更新 .env 配置**:
   ```bash
   PRODUCTION_DOMAIN=your-domain.com
   ALLOWED_HOSTS=your-domain.com,149.104.29.136
   DEBUG=False
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

4. **前端配置**: 在 `front/src/api/config.js` 中使用域名而非 IP

### 快速诊断命令
```bash
# 1. 检查环境变量是否生效
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py shell
```

在 shell 中:
```python
from django.conf import settings
print("DEBUG:", settings.DEBUG)
print("ALLOWED_HOSTS:", settings.ALLOWED_HOSTS)
print("CSRF_TRUSTED_ORIGINS:", settings.CSRF_TRUSTED_ORIGINS)
```

```bash
# 2. 检查数据库是否有数据
python manage.py shell
```
```python
from songs.models import CompetitionPhase
print(CompetitionPhase.objects.count())  # 应该 > 0
```

---

## 问题 1: Admin 管理员无法登录 - 密码错误

### 症状
- 访问 `/admin/` 时输入用户名和密码显示"密码错误"
- 确认输入的密码是正确的

### 可能原因和解决方案

#### 原因 A: 超级用户尚未创建
**检查方法**:
```bash
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py shell
```

然后在 Python shell 中执行:
```python
from django.contrib.auth.models import User
User.objects.filter(is_superuser=True).count()
# 如果返回 0，说明没有超级用户
```

**解决方法**:
```bash
# 创建超级用户
python manage.py createsuperuser

# 按提示输入:
# - 用户名 (例如: admin)
# - 邮箱 (可选，直接回车跳过)
# - 密码 (输入两次确认，注意至少8位且不能全是数字)
```

#### 原因 B: 数据库迁移不完整
**检查方法**:
```bash
python manage.py showmigrations
# 查看是否所有迁移都有 [X] 标记
```

**解决方法**:
```bash
python manage.py migrate
```

#### 原因 C: 数据库文件权限问题
**检查方法**:
```bash
ls -la /opt/xmmcg/backend/xmmcg/db.sqlite3
```

**解决方法**:
```bash
# 确保 www-data 用户有读写权限
sudo chown www-data:www-data /opt/xmmcg/backend/xmmcg/db.sqlite3
sudo chmod 664 /opt/xmmcg/backend/xmmcg/db.sqlite3
```

#### 原因 D: 重置管理员密码
如果确定超级用户存在但密码忘记了:
```bash
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py changepassword admin
# 或者使用 shell:
python manage.py shell
```

在 shell 中:
```python
from django.contrib.auth.models import User
user = User.objects.get(username='admin')
user.set_password('new_password_here')
user.save()
exit()
```

---

## 问题 2: Cross-Origin-Opener-Policy (COOP) 警告

### 症状
浏览器控制台显示:
```
The Cross-Origin-Opener-Policy header has been ignored, because 
the URL's origin was untrustworthy. It was defined either in the 
final response or a redirect. Please deliver the response using 
the HTTPS protocol.
```

### 原因
Django 的 `SecurityMiddleware` 默认设置了 COOP 头，但该安全特性仅在 HTTPS 环境下有效。

### 解决方案

#### 方案 A: 配置 HTTPS (推荐用于生产环境)
```bash
# 安装 SSL 证书 (使用 Let's Encrypt)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Certbot 会自动:
# 1. 获取 SSL 证书
# 2. 修改 Nginx 配置启用 HTTPS
# 3. 设置自动续期
```

然后在 `/opt/xmmcg/.env` 中启用 HTTPS 安全设置:
```bash
DEBUG=False
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

重启服务:
```bash
sudo systemctl restart gunicorn nginx
```

#### 方案 B: 临时禁用 COOP (仅用于开发/测试)
在 `/opt/xmmcg/.env` 中设置:
```bash
DEBUG=True
SECURE_CROSS_ORIGIN_OPENER_POLICY=None
```

或者在 `settings.py` 中已经自动处理:
- 当 `DEBUG=True` 时，COOP 自动禁用
- 当 `DEBUG=False` 时，COOP 根据环境变量配置

重启 Gunicorn:
```bash
sudo systemctl restart gunicorn
```

#### 方案 C: 使用 localhost 访问 (开发环境)
如果在本地开发，直接使用 `http://localhost:端口` 访问即可避免此警告。

---

## 问题 3: 静态文件 404 错误

### 症状
- CSS、JS 文件无法加载
- Admin 页面样式丢失
- 前端资源返回 404

### 解决方案
```bash
# 1. 确认静态文件目录权限
sudo chown -R www-data:www-data /var/www/xmmcg/
sudo chmod -R 755 /var/www/xmmcg/

# 2. 重新收集静态文件
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py collectstatic --noinput

# 3. 检查 Nginx 配置
sudo nginx -t
sudo systemctl reload nginx
```

---

## 问题 4: Gunicorn 服务无法启动

### 检查服务状态
```bash
sudo systemctl status gunicorn
sudo journalctl -u gunicorn -n 50
```

### 常见错误和解决方案

#### 错误: "ModuleNotFoundError"
```bash
# 确保虚拟环境已安装所有依赖
source /opt/xmmcg/venv/bin/activate
pip install -r /opt/xmmcg/backend/xmmcg/requirements.txt
sudo systemctl restart gunicorn
```

#### 错误: "Address already in use"
```bash
# 查找占用 socket 的进程
sudo lsof /run/gunicorn.sock
# 或
sudo fuser /run/gunicorn.sock

# 杀死进程
sudo systemctl stop gunicorn
sudo rm /run/gunicorn.sock
sudo systemctl start gunicorn
```

#### 错误: "Permission denied"
```bash
# 检查目录权限
sudo chown -R www-data:www-data /opt/xmmcg/
sudo chmod -R 755 /opt/xmmcg/

# 数据库文件权限
sudo chown www-data:www-data /opt/xmmcg/backend/xmmcg/db.sqlite3
sudo chmod 664 /opt/xmmcg/backend/xmmcg/db.sqlite3
```

---

## 问题 5: 数据库迁移冲突

### 症状
```
django.db.migrations.exceptions.InconsistentMigrationHistory
```

### 解决方案
```bash
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate

# 检查迁移状态
python manage.py showmigrations

# 如果有冲突的迁移文件
# 方案 A: 重置应用迁移 (谨慎使用，会丢失数据)
python manage.py migrate songs zero
python manage.py migrate songs

# 方案 B: 伪造迁移
python manage.py migrate --fake songs 0007

# 方案 C: 清理并重新迁移 (开发环境)
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

---

## 问题 6: CORS 跨域错误

### 症状
浏览器控制台显示:
```
Access to XMLHttpRequest at 'http://domain.com/api/...' from origin 
'http://domain.com' has been blocked by CORS policy
```

### 解决方案
在 `/opt/xmmcg/.env` 中添加:
```bash
PRODUCTION_DOMAIN=your-domain.com
```

或直接在 `settings.py` 的 `CORS_ALLOWED_ORIGINS` 中添加你的域名。

重启服务:
```bash
sudo systemctl restart gunicorn
```

---

## 问题 7: 前端无法访问 (Nginx 404)

### 检查 Nginx 配置
```bash
sudo nginx -t
cat /etc/nginx/sites-available/xmmcg
```

### 确认前端文件存在
```bash
ls -la /var/www/xmmcg/frontend/
# 应该看到 index.html 和 assets/ 目录
```

### 重新构建前端
```bash
cd /opt/xmmcg/front
npm install
npm run build

# 复制到部署目录
sudo rm -rf /var/www/xmmcg/frontend/*
sudo cp -r dist/* /var/www/xmmcg/frontend/
sudo chown -R www-data:www-data /var/www/xmmcg/frontend/
```

---

## 快速诊断命令集

### 检查所有服务状态
```bash
# 服务状态
sudo systemctl status gunicorn nginx

# 端口监听
sudo ss -tulnp | grep -E ':(80|443|8000)'

# 日志查看
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
sudo journalctl -u gunicorn -f
```

### 检查文件权限
```bash
# 代码目录
ls -la /opt/xmmcg/

# 静态文件
ls -la /var/www/xmmcg/

# 数据库
ls -la /opt/xmmcg/backend/xmmcg/db.sqlite3

# Socket 文件
ls -la /run/gunicorn.sock
```

### 测试 API 连接
```bash
# 测试 Gunicorn (通过 Unix Socket)
curl --unix-socket /run/gunicorn.sock http://localhost/api/songs/

# 测试 Nginx
curl http://localhost/api/songs/
curl http://localhost/

# 从外部测试
curl http://your-domain.com/api/songs/
```

---

## 环境变量配置检查清单

确保 `/opt/xmmcg/.env` 包含以下配置:

```bash
# Django Core
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Production Domain
PRODUCTION_DOMAIN=your-domain.com

# Security (HTTPS 启用后)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# Majdata Configuration
ENABLE_CHART_FORWARD_TO_MAJDATA=True
MAJDATA_USERNAME=your_username
MAJDATA_PASSWD_HASHED=your_md5_hashed_password
```

---

## 获取帮助

如果以上方法都无法解决问题:

1. **查看完整日志**:
   ```bash
   sudo journalctl -u gunicorn -n 100 --no-pager
   sudo cat /var/log/nginx/error.log
   ```

2. **启用 Django DEBUG 模式** (临时):
   ```bash
   # 在 .env 中设置
   DEBUG=True
   # 重启服务查看详细错误
   sudo systemctl restart gunicorn
   ```

3. **检查防火墙**:
   ```bash
   sudo ufw status
   # 确保 80 和 443 端口开放
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

4. **验证 DNS 解析**:
   ```bash
   nslookup your-domain.com
   # 确保指向正确的服务器 IP
   ```
