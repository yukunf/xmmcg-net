# xmmcg-net

这是 XMMCG 比赛专用网站的源代码仓库。
：我能在不懂一行vue的情况下写出一个网站吗？
：可以，但是我要死了

--
**技术栈**：前端Vue.js + Element Plus（控件样式），后端Django + Pillow库处理图片。部署使用debian服务器+常规的gunicron作为WSGI + nginx转发。（不过我被nginx折磨得要死）

## 环境变量配置

项目使用 **python-decouple** 管理敏感配置信息，避免将密钥硬编码在代码中。

### 配置文件位置
项目支持两个环境变量文件（按优先级）：
1. **`login_credentials.env`**（项目根目录） - 用于存储敏感的登录凭证
2. **`.env`**（项目根目录） - 用于其他环境变量

### 必需配置项

在项目根目录创建 `login_credentials.env` 文件，包含以下内容：

```env
# Django 密钥（生产环境必须更改）
SECRET_KEY=your-secret-key-here

# Majdata.net API 凭证
MAJDATA_USERNAME=xmmcg5
MAJDATA_PASSWD_HASHED=your-hashed-password-here
```

### 可选配置项

```env
# 调试模式（生产环境设为 False）
DEBUG=True

# 允许的主机（逗号分隔）
ALLOWED_HOSTS=localhost,127.0.0.1

# Majdata.net 集成开关
ENABLE_CHART_FORWARD_TO_MAJDATA=True

# Majdata.net API 地址（默认值可不设置）
MAJDATA_BASE_URL=https://majdata.net/api3/api/
MAJDATA_LOGIN_URL=https://majdata.net/api3/api/account/Login
MAJDATA_UPLOAD_URL=https://majdata.net/api3/api/maichart/upload
```

### 获取配置值

所有配置在 [backend/xmmcg/xmmcg/settings.py](backend/xmmcg/xmmcg/settings.py) 中已自动加载：

```python
from decouple import config, Csv

# 带默认值的配置
DEBUG = config('DEBUG', default=False, cast=bool)

# 必需配置（无默认值，缺失时报错）
SECRET_KEY = config('SECRET_KEY')

# CSV 列表配置
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
```

### 安全提示

⚠️ **重要**：
- `.env` 和 `login_credentials.env` 已添加到 `.gitignore`，**请勿提交到版本控制**
- 生产环境必须修改 `SECRET_KEY` 和 `MAJDATA_PASSWD_HASHED`
- 使用以下命令生成新密钥：
  ```bash
  python backend/xmmcg/manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```

## 快速开始

### 后端设置

```bash
cd backend/xmmcg
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 前端设置

```bash
cd front
npm install
npm run dev
```

详细文档请参阅：
- [后端 README](backend/xmmcg/README.md) - Django 项目说明
- [前端 README](front/README.md) - Vue 3 项目说明
- [BIDDING_SYSTEM_GUIDE.md](BIDDING_SYSTEM_GUIDE.md) - 竞标系统详细说明
- [COMPETITION_PHASE_SYSTEM.md](COMPETITION_PHASE_SYSTEM.md) - 比赛阶段管理
- [PEER_REVIEW_SYSTEM.md](PEER_REVIEW_SYSTEM.md) - 同行评审系统

这是xmmcg比赛专用网站xmmcgnet的源代码仓库。
---

## 数据库备份配置

项目提供了自动化的 SQLite 数据库备份方案，支持定时备份、自动压缩和清理旧备份。

### 备份脚本说明

#### 核心脚本：[scripts/backup_sqlite.sh](scripts/backup_sqlite.sh)

该脚本提供以下功能：
- ✅ 使用 SQLite 原子备份命令（`.backup`），不会锁死数据库
- 🗜️ 自动压缩备份文件（gzip），节省磁盘空间
- 🗑️ 自动删除 30 天前的旧备份
- 📅 备份文件命名格式：`db_backup_YYYYMMDD_HHMMSS.sqlite3.gz`

**配置项（编辑脚本头部）**：
```bash
DB_DIR="/opt/xmmcg/backend/xmmcg/"    # 数据库所在目录
BACKUP_DIR="/var/back/xmmcg/"         # 备份存放目录
DB_NAME="db.sqlite3"                  # 数据库文件名
```

### 方案一：使用 systemd（推荐 - Debian/Ubuntu）

#### 1. 安装服务文件

```bash
# 复制服务和定时器文件到 systemd 目录
sudo cp scripts/django-backup.service /etc/systemd/system/
sudo cp scripts/django-backup.timer /etc/systemd/system/

# 修改 backup_sqlite.sh 中的路径，确保指向正确的数据库和备份目录
sudo nano scripts/backup_sqlite.sh

# 赋予脚本执行权限
sudo chmod +x scripts/backup_sqlite.sh
```

#### 2. 配置服务文件

编辑 [scripts/django-backup.service](scripts/django-backup.service)，设置正确的用户：

```ini
[Service]
User=root  # 或改为你的实际用户名（如 ubuntu）
ExecStart=/opt/xmmcg/scripts/backup_sqlite.sh
```

⚠️ **权限注意**：
- 确保指定的用户有权限读写数据库目录和备份目录
- 如使用非 root 用户，需提前创建备份目录并设置权限：
  ```bash
  sudo mkdir -p /var/back/xmmcg
  sudo chown your-user:your-user /var/back/xmmcg
  ```

#### 3. 启用和启动定时器

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用定时器（开机自启）
sudo systemctl enable django-backup.timer

# 立即启动定时器
sudo systemctl start django-backup.timer

# 查看定时器状态
sudo systemctl status django-backup.timer

# 查看下次执行时间
sudo systemctl list-timers --all | grep django-backup
```

#### 4. 手动执行备份（测试）

```bash
# 测试备份脚本
sudo /opt/xmmcg/scripts/backup_sqlite.sh

# 或通过服务执行
sudo systemctl start django-backup.service

# 查看执行日志
sudo journalctl -u django-backup.service -n 50
```

#### 5. 定时器配置

[scripts/django-backup.timer](scripts/django-backup.timer) 默认配置：
- **执行时间**：每天凌晨 3:00
- **Persistent=true**：如果关机错过执行时间，开机后会立即补执行

修改执行时间（编辑 `.timer` 文件）：
```ini
# 每天凌晨 2:30
OnCalendar=*-*-* 02:30:00

# 每 6 小时执行一次
OnCalendar=*-*-* 0/6:00:00

# 每周日凌晨 4:00
OnCalendar=Sun *-*-* 04:00:00
```

### 方案二：使用 crontab

如果不使用 systemd，可以使用传统的 cron 定时任务。参考 [scripts/crontab.example](scripts/crontab.example) 文件。

#### 1. 编辑 crontab

```bash
crontab -e
```

#### 2. 添加备份任务

```cron
# 每天凌晨 3:00 执行备份
0 3 * * * /opt/xmmcg/scripts/backup_sqlite.sh

# 或每 12 小时备份一次
0 */12 * * * /opt/xmmcg/scripts/backup_sqlite.sh
```

#### 3. 验证配置

```bash
# 查看当前 crontab 任务
crontab -l

# 查看 cron 服务状态
sudo systemctl status cron
```

### 恢复备份

从备份恢复数据库：

```bash
# 1. 停止 Django 服务
sudo systemctl stop gunicorn

# 2. 解压备份文件
gunzip /var/back/xmmcg/db_backup_20260131_030000.sqlite3.gz

# 3. 替换当前数据库（建议先备份当前数据库）
cp /opt/xmmcg/backend/xmmcg/db.sqlite3 /opt/xmmcg/backend/xmmcg/db.sqlite3.old
cp /var/back/xmmcg/db_backup_20260131_030000.sqlite3 /opt/xmmcg/backend/xmmcg/db.sqlite3

# 4. 恢复服务权限
sudo chown www-data:www-data /opt/xmmcg/backend/xmmcg/db.sqlite3  # 根据实际用户调整

# 5. 重启 Django 服务
sudo systemctl start gunicorn
```

### 监控和维护

```bash
# 查看备份文件列表
ls -lh /var/back/xmmcg/

# 查看磁盘使用情况
du -sh /var/back/xmmcg/

# 查看 systemd 备份日志
sudo journalctl -u django-backup.service --since "1 week ago"

# 查看 systemd 定时器列表
sudo systemctl list-timers
```

### 前置要求

确保系统已安装 SQLite 命令行工具：

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install sqlite3

# 验证安装
sqlite3 --version
```

---

