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
SECRET_KEY=生成的随机密钥
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,your-server-ip

# 生产域名
PRODUCTION_DOMAIN=your-domain.com

# Majdata API 配置
MAJDATA_USERNAME=your-username
MAJDATA_PASSWD_HASHED=your-hashed-password
```

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

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `SECRET_KEY` | Django 加密密钥 | 自动生成 |
| `DEBUG` | 调试模式（生产环境必须为 False） | `False` |
| `ALLOWED_HOSTS` | 允许访问的主机名 | `domain.com,ip` |
| `PRODUCTION_DOMAIN` | 生产环境域名 | `xmmcg.net` |
| `MAJDATA_USERNAME` | Majdata API 用户名 | `xmmcg5` |
| `MAJDATA_PASSWD_HASHED` | Majdata API 密码哈希 | `your-hash` |

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

### 问题 1: 502 Bad Gateway

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

### 问题 2: 静态文件 404

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

### 问题 3: 数据库迁移失败

**原因**: 迁移文件冲突

**解决**:
```bash
# 备份数据库
cd /opt/xmmcg/backend/xmmcg
cp db.sqlite3 db.sqlite3.backup

# 查看迁移状态
source /opt/xmmcg/venv/bin/activate
python manage.py showmigrations

# 方案1: 假迁移（有数据时）
python manage.py migrate --fake songs 0007

# 方案2: 重置数据库（无重要数据时）
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### 问题 4: 文件上传失败

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

### 问题 5: CORS 错误

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

### 问题 6: Git 权限错误

**错误**: `fatal: detected dubious ownership`

**解决**:
```bash
git config --global --add safe.directory /opt/xmmcg
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
