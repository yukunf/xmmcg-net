# 服务器快速修复指南 (149.104.29.136)

## 🚨 紧急修复：500 错误 + HTTPS 警告

### 在服务器上执行以下命令

```bash
# 1. 编辑环境配置
sudo nano /opt/xmmcg/.env
```

添加或修改以下内容：
```bash
# === 必须配置项 ===
DEBUG=True
SECRET_KEY=xmmcg-production-secret-key-change-this-in-production
ALLOWED_HOSTS=149.104.29.136,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://149.104.29.136,http://149.104.29.136

# === 可选配置项 ===
# 如果有域名，取消下面的注释并填写
# PRODUCTION_DOMAIN=your-domain.com

# === Majdata 配置 (可选) ===
# ENABLE_CHART_FORWARD_TO_MAJDATA=False
# MAJDATA_USERNAME=your_username
# MAJDATA_PASSWD_HASHED=your_md5_password
```

保存并退出 (Ctrl+O, Enter, Ctrl+X)

```bash
# 2. 初始化数据库
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py migrate
python manage.py add_sample_data  # 创建测试数据

# 3. 创建管理员账户
python manage.py createsuperuser
# 输入: 用户名 admin, 邮箱留空, 密码 admin123 (或你自己的密码)

# 4. 重启服务
sudo systemctl restart gunicorn
sudo systemctl status gunicorn

# 5. 查看日志确认无错误
sudo journalctl -u gunicorn -n 20
```

### 测试是否修复成功

```bash
# 在服务器本地测试
curl http://localhost/api/songs/phases/
# 应该返回 JSON 数据

# 测试前端
curl http://localhost/ | head -n 5
# 应该返回 HTML
```

---

## 🔐 关于 HTTPS 警告

### 为什么会出现 SSL 警告？

**原因**: 你用的是自签名证书或 IP 地址，浏览器无法验证证书的有效性。

### 临时解决方案（仅测试用）

**方案 A**: 使用 HTTP 访问
```
http://149.104.29.136  ← 使用这个，不用 https://
```

**方案 B**: 浏览器强制信任
1. 访问 `https://149.104.29.136`
2. 看到警告时点击"高级"
3. 点击"继续访问不安全的网站"（仅限测试环境！）

### 正确解决方案（生产环境必须）

**需要域名 + Let's Encrypt 证书**

1. **购买并配置域名**:
   - 购买域名（如 GoDaddy、Namecheap、阿里云等）
   - 添加 A 记录: `@ → 149.104.29.136`
   - 添加 A 记录: `www → 149.104.29.136`

2. **安装 SSL 证书**:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
   ```

3. **更新配置**:
   编辑 `/opt/xmmcg/.env`:
   ```bash
   DEBUG=False
   PRODUCTION_DOMAIN=yourdomain.com
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,149.104.29.136
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

4. **重启服务**:
   ```bash
   sudo systemctl restart gunicorn nginx
   ```

---

## 📊 验证配置是否正确

### 检查环境变量
```bash
cd /opt/xmmcg/backend/xmmcg
source /opt/xmmcg/venv/bin/activate
python manage.py shell
```

在 Python shell 中执行:
```python
from django.conf import settings

# 检查关键配置
print("DEBUG:", settings.DEBUG)
print("ALLOWED_HOSTS:", settings.ALLOWED_HOSTS)
print("CSRF_TRUSTED_ORIGINS:", settings.CSRF_TRUSTED_ORIGINS)

# 应该输出:
# DEBUG: True
# ALLOWED_HOSTS: ['149.104.29.136', 'localhost', '127.0.0.1']
# CSRF_TRUSTED_ORIGINS: ['http://localhost:3000', ..., 'https://149.104.29.136', 'http://149.104.29.136']

exit()
```

### 检查数据库数据
```bash
python manage.py shell
```
```python
from songs.models import CompetitionPhase, Song, User
print("CompetitionPhase 数量:", CompetitionPhase.objects.count())
print("Song 数量:", Song.objects.count())
print("User 数量:", User.objects.count())

# 列出所有阶段
for phase in CompetitionPhase.objects.all():
    print(f"- {phase.name} ({phase.slug})")
exit()
```

### 检查服务状态
```bash
# Gunicorn 状态
sudo systemctl status gunicorn | head -n 15

# Nginx 状态
sudo systemctl status nginx | head -n 10

# 端口监听
sudo ss -tulnp | grep -E ':(80|443|8000)'
```

---

## 🛠️ 常见问题排查

### API 仍然返回 500
```bash
# 查看详细错误日志
sudo journalctl -u gunicorn -n 100 --no-pager

# 临时启用 Django 调试
# 在 .env 中设置 DEBUG=True 然后重启
sudo systemctl restart gunicorn
```

### 前端无法访问
```bash
# 检查前端文件是否存在
ls -la /var/www/xmmcg/frontend/

# 应该看到 index.html 和 assets/
# 如果没有，重新部署前端:
cd /opt/xmmcg/front
npm install
npm run build
sudo cp -r dist/* /var/www/xmmcg/frontend/
sudo chown -R www-data:www-data /var/www/xmmcg/frontend/
```

### Nginx 配置错误
```bash
# 测试配置
sudo nginx -t

# 如果报错，检查配置文件
sudo nano /etc/nginx/sites-available/xmmcg

# 重新加载
sudo systemctl reload nginx
```

---

## 📝 配置文件位置速查

| 文件 | 路径 | 用途 |
|------|------|------|
| 环境变量 | `/opt/xmmcg/.env` | Django 配置、密钥、域名 |
| 数据库 | `/opt/xmmcg/backend/xmmcg/db.sqlite3` | SQLite 数据库 |
| Gunicorn 服务 | `/etc/systemd/system/gunicorn.service` | 后端服务配置 |
| Nginx 配置 | `/etc/nginx/sites-available/xmmcg` | Web 服务器配置 |
| 静态文件 | `/var/www/xmmcg/static/` | Django 静态文件 |
| 前端文件 | `/var/www/xmmcg/frontend/` | Vue 打包文件 |
| 日志 | `sudo journalctl -u gunicorn` | 后端运行日志 |
| Nginx 日志 | `/var/log/nginx/error.log` | Web 服务器错误 |

---

## 🎯 下一步建议

✅ **立即执行** (修复 500 错误):
1. 配置 `.env` 文件添加 IP 地址
2. 运行数据库迁移和初始化
3. 创建管理员账户
4. 重启服务

⚠️ **短期内完成** (提升安全性):
1. 生成强随机的 `SECRET_KEY`
2. 购买域名并配置 DNS
3. 安装 Let's Encrypt SSL 证书
4. 设置 `DEBUG=False`

🚀 **生产就绪**:
1. 配置备份策略
2. 设置监控告警
3. 优化性能配置
4. 准备灾难恢复方案
