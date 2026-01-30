# XMMCG 生产环境部署指南 - Debian/Ubuntu

## 📋 目录
- [时区配置](#时区配置)
- [脚本部署](#脚本部署)
- [Cron 定时任务](#cron-定时任务)
- [验证测试](#验证测试)
- [故障排查](#故障排查)

---

## ⏰ 时区配置

### 1. 设置系统时区（中国标准时间）

```bash
# 查看当前时区
timedatectl

# 设置为中国标准时间
sudo timedatectl set-timezone Asia/Shanghai

# 验证
timedatectl
# 输出应包含：Time zone: Asia/Shanghai (CST, +0800)

# 同步系统时间（可选）
sudo apt-get install -y ntpdate
sudo ntpdate ntp.ubuntu.com
```

### 2. Django 时区配置

已在 `settings.py` 中配置：

```python
# backend/xmmcg/xmmcg/settings.py
TIME_ZONE = 'Asia/Shanghai'  # 中国标准时间
USE_TZ = True                 # 启用时区支持
LANGUAGE_CODE = 'zh-hans'     # 中文简体
```

可通过环境变量覆盖（`.env` 文件）：

```bash
TIME_ZONE=Asia/Shanghai
```

### 3. 验证时区一致性

```bash
# 在 Django shell 中验证
cd /var/www/xmmcg-net/backend/xmmcg
source /var/www/xmmcg-net/.venv/bin/activate
python manage.py shell

# Python shell 中执行：
>>> from django.utils import timezone
>>> from django.conf import settings
>>> print(f"Django TIME_ZONE: {settings.TIME_ZONE}")
>>> print(f"Current time: {timezone.now()}")
>>> print(f"Local time: {timezone.localtime()}")
```

---

## 📦 脚本部署

### 1. 上传脚本到服务器

```bash
# 将脚本上传到服务器
scp scripts/*.sh your-server:/var/www/xmmcg-net/scripts/
scp scripts/crontab.example your-server:/var/www/xmmcg-net/scripts/

# 或者通过 Git 拉取
cd /var/www/xmmcg-net
git pull origin main
```

### 2. 修改脚本中的路径

编辑脚本，将路径改为实际部署路径：

```bash
# 编辑更新脚本
nano /var/www/xmmcg-net/scripts/update_phase_linux.sh
nano /var/www/xmmcg-net/scripts/smart_update_phase.sh

# 修改以下变量（根据实际情况）：
PROJECT_ROOT="/var/www/xmmcg-net"          # 项目根目录
BACKEND_DIR="${PROJECT_ROOT}/backend/xmmcg"  # Django 项目目录
VENV_PATH="${PROJECT_ROOT}/.venv"          # 虚拟环境路径
```

### 3. 设置脚本执行权限

```bash
chmod +x /var/www/xmmcg-net/scripts/update_phase_linux.sh
chmod +x /var/www/xmmcg-net/scripts/smart_update_phase.sh

# 验证权限
ls -lh /var/www/xmmcg-net/scripts/*.sh
# 输出应显示 -rwxr-xr-x
```

### 4. 创建日志目录

```bash
mkdir -p /var/www/xmmcg-net/logs
chmod 755 /var/www/xmmcg-net/logs

# 确保 Web 服务器用户有写权限（如果脚本由 www-data 运行）
chown -R your-user:www-data /var/www/xmmcg-net/logs
```

---

## 🕐 Cron 定时任务

### 方案选择

| 方案 | 频率 | 适用场景 | 优点 | 缺点 |
|------|------|---------|------|------|
| **方案 A** | 每小时固定 | 小型项目 | 简单可靠 | 不够及时 |
| **方案 B** | 智能调整 | 生产环境 | 平衡资源和及时性 | 稍复杂 |
| **方案 C** | 组合式 | 大型项目 | 精细控制 | 配置复杂 |

### 推荐配置：方案 B（智能频率）

```bash
# 1. 编辑 crontab
crontab -e

# 2. 添加以下行（根据实际路径修改）
*/10 * * * * /var/www/xmmcg-net/scripts/smart_update_phase.sh

# 3. 保存退出（Ctrl+X, Y, Enter）

# 4. 验证
crontab -l
```

**工作原理：**
- 每 10 分钟运行一次检查脚本
- **平时**：只在整点执行更新（每小时 1 次）
- **阶段切换前 2 小时**：每 10 分钟执行 1 次
- 自动根据距离下次切换的时间调整频率

### 简单配置：方案 A（固定频率）

```bash
# 每小时整点执行
0 * * * * /var/www/xmmcg-net/scripts/update_phase_linux.sh
```

### 精细配置：方案 C（组合式）

```bash
# 白天高频（8:00-22:00，每 30 分钟）
0,30 8-22 * * * /var/www/xmmcg-net/scripts/update_phase_linux.sh

# 夜间低频（每 2 小时）
0 0,2,4,6 * * * /var/www/xmmcg-net/scripts/update_phase_linux.sh

# 周日凌晨清理日志
0 3 * * 0 tail -n 100 /var/www/xmmcg-net/logs/phase_update.log > /tmp/phase_update.tmp && mv /tmp/phase_update.tmp /var/www/xmmcg-net/logs/phase_update.log
```

---

## ✅ 验证测试

### 1. 手动执行脚本测试

```bash
# 激活虚拟环境
source /var/www/xmmcg-net/.venv/bin/activate

# 测试更新命令（干运行）
cd /var/www/xmmcg-net/backend/xmmcg
python manage.py update_phase_status --dry-run

# 测试更新脚本
/var/www/xmmcg-net/scripts/update_phase_linux.sh

# 测试智能脚本
/var/www/xmmcg-net/scripts/smart_update_phase.sh

# 检查日志
tail -f /var/www/xmmcg-net/logs/phase_update.log
tail -f /var/www/xmmcg-net/logs/smart_update.log
```

### 2. 验证 Cron 是否正常工作

```bash
# 查看 cron 服务状态
sudo systemctl status cron

# 如果未运行，启动它
sudo systemctl start cron
sudo systemctl enable cron

# 查看 cron 日志
sudo tail -f /var/log/syslog | grep CRON

# 或者（Debian/Ubuntu）
sudo tail -f /var/log/cron
```

### 3. 强制执行一次并验证

```bash
# 手动触发 cron 任务（等待下一个 10 分钟标记）
# 或者直接运行脚本
/var/www/xmmcg-net/scripts/smart_update_phase.sh

# 检查是否有新日志
tail -20 /var/www/xmmcg-net/logs/phase_update.log

# 验证数据库中的 is_active 状态
cd /var/www/xmmcg-net/backend/xmmcg
source /var/www/xmmcg-net/.venv/bin/activate
python manage.py shell

# 在 shell 中：
>>> from songs.models import CompetitionPhase
>>> for p in CompetitionPhase.objects.all():
...     print(f"{p.name}: is_active={p.is_active}, status={p.status}")
```

### 4. 模拟阶段切换测试

```bash
# 创建一个即将开始的测试阶段（1 分钟后）
python manage.py shell

>>> from django.utils import timezone
>>> from datetime import timedelta
>>> from songs.models import CompetitionPhase
>>> 
>>> test_phase = CompetitionPhase.objects.create(
...     name="测试阶段",
...     phase_key="test_phase",
...     description="测试用",
...     start_time=timezone.now() + timedelta(minutes=1),
...     end_time=timezone.now() + timedelta(hours=1),
...     is_active=False,
...     order=999
... )
>>> print(f"Created test phase: {test_phase.id}")
>>> exit()

# 等待 1 分钟，然后手动执行更新
sleep 60
python manage.py update_phase_status

# 验证 is_active 是否变为 True
python manage.py shell
>>> from songs.models import CompetitionPhase
>>> p = CompetitionPhase.objects.get(phase_key="test_phase")
>>> print(f"is_active: {p.is_active}")  # 应该是 True

# 清理测试数据
>>> p.delete()
>>> exit()
```

---

## 🔧 故障排查

### 问题 1：脚本无法执行

**检查清单：**
```bash
# 1. 检查文件权限
ls -lh /var/www/xmmcg-net/scripts/*.sh

# 2. 检查脚本路径
which python
which bash

# 3. 检查虚拟环境
source /var/www/xmmcg-net/.venv/bin/activate
python --version

# 4. 手动执行脚本查看错误
bash -x /var/www/xmmcg-net/scripts/update_phase_linux.sh
```

### 问题 2：Cron 任务不执行

**检查清单：**
```bash
# 1. 确认 cron 服务运行中
sudo systemctl status cron

# 2. 查看 crontab 配置
crontab -l

# 3. 检查 cron 日志
sudo tail -100 /var/log/syslog | grep CRON

# 4. 使用绝对路径
# 将 crontab 中的路径改为绝对路径
*/10 * * * * /bin/bash /var/www/xmmcg-net/scripts/smart_update_phase.sh

# 5. 添加环境变量
# 在 crontab 顶部添加：
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

### 问题 3：时区不一致

**检查清单：**
```bash
# 1. 检查系统时区
timedatectl

# 2. 检查 Django 时区
cd /var/www/xmmcg-net/backend/xmmcg
source /var/www/xmmcg-net/.venv/bin/activate
python manage.py shell
>>> from django.conf import settings
>>> print(settings.TIME_ZONE)

# 3. 统一时区
sudo timedatectl set-timezone Asia/Shanghai

# 4. 重启 Django 应用
sudo systemctl restart gunicorn  # 或你的 WSGI 服务
```

### 问题 4：日志文件写入失败

**检查清单：**
```bash
# 1. 检查日志目录权限
ls -ld /var/www/xmmcg-net/logs

# 2. 检查日志文件权限
ls -lh /var/www/xmmcg-net/logs/*.log

# 3. 修复权限
chmod 755 /var/www/xmmcg-net/logs
chmod 644 /var/www/xmmcg-net/logs/*.log

# 4. 如果 cron 以其他用户运行
sudo chown -R your-user:your-group /var/www/xmmcg-net/logs
```

### 问题 5：智能脚本无法计算时间

**检查清单：**
```bash
# 1. 手动运行 Python 计算部分
source /var/www/xmmcg-net/.venv/bin/activate
cd /var/www/xmmcg-net/backend/xmmcg

python << 'EOF'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.utils import timezone
from songs.models import CompetitionPhase

now = timezone.now()
print(f"Current time: {now}")

phases = CompetitionPhase.objects.filter(is_active=True)
print(f"Active phases: {phases.count()}")
for p in phases:
    print(f"  - {p.name}: {p.start_time} to {p.end_time}")
EOF

# 2. 如果 Django 导入失败
pip install django
# 检查 settings.py 是否正确
```

---

## 📊 监控建议

### 1. 日志监控

```bash
# 安装日志监控工具（可选）
sudo apt-get install -y logwatch

# 配置每日日志报告
sudo nano /etc/logwatch/conf/logfiles/xmmcg-phase.conf
```

### 2. 邮件告警（可选）

```bash
# 安装邮件工具
sudo apt-get install -y mailutils

# 在 crontab 中添加 MAILTO
crontab -e

# 在顶部添加：
MAILTO=your-email@example.com
```

### 3. 健康检查脚本

```bash
# 创建健康检查脚本
cat > /var/www/xmmcg-net/scripts/health_check.sh << 'EOF'
#!/bin/bash
LOG_FILE="/var/www/xmmcg-net/logs/phase_update.log"
LAST_UPDATE=$(tail -1 "$LOG_FILE" | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')

# 检查最后更新是否在 2 小时内
# ... 添加检查逻辑
EOF

chmod +x /var/www/xmmcg-net/scripts/health_check.sh

# 添加到 crontab（每 6 小时检查一次）
0 */6 * * * /var/www/xmmcg-net/scripts/health_check.sh
```

---

## 🎯 快速部署（一键脚本）

```bash
#!/bin/bash
# 快速部署脚本

set -e

PROJECT_ROOT="/var/www/xmmcg-net"

echo "=== XMMCG Phase Update Deployment ==="

# 1. 设置系统时区
echo "[1/6] Setting timezone..."
sudo timedatectl set-timezone Asia/Shanghai

# 2. 设置脚本权限
echo "[2/6] Setting script permissions..."
chmod +x ${PROJECT_ROOT}/scripts/*.sh

# 3. 创建日志目录
echo "[3/6] Creating log directory..."
mkdir -p ${PROJECT_ROOT}/logs
chmod 755 ${PROJECT_ROOT}/logs

# 4. 测试脚本
echo "[4/6] Testing scripts..."
source ${PROJECT_ROOT}/.venv/bin/activate
cd ${PROJECT_ROOT}/backend/xmmcg
python manage.py update_phase_status --dry-run

# 5. 配置 crontab
echo "[5/6] Setting up crontab..."
(crontab -l 2>/dev/null; echo "*/10 * * * * ${PROJECT_ROOT}/scripts/smart_update_phase.sh") | crontab -

# 6. 验证
echo "[6/6] Verifying..."
crontab -l
timedatectl

echo "=== Deployment completed! ==="
echo "Check logs: tail -f ${PROJECT_ROOT}/logs/phase_update.log"
```

保存为 `deploy_phase_update.sh` 并执行：

```bash
chmod +x deploy_phase_update.sh
./deploy_phase_update.sh
```

---

## 📚 参考资料

- [Django 时区文档](https://docs.djangoproject.com/en/stable/topics/i18n/timezones/)
- [Crontab 语法](https://crontab.guru/)
- [systemd timer](https://www.freedesktop.org/software/systemd/man/systemd.timer.html) - Cron 的现代替代方案
- [Debian 时区配置](https://wiki.debian.org/TimeZoneChanges)

---

**部署完成后，系统将自动维护阶段状态，确保竞标系统的权限控制始终准确！** 🎉
