# XMMCG Phase Status Update - Systemd 配置

## 概述

这个目录包含了用于自动更新 XMMCG 比赛阶段状态的 systemd 配置文件。

## 文件说明

- `xmmcg-phase-update.service` - systemd 服务单元文件
- `xmmcg-phase-update.timer` - systemd 定时器配置（每10分钟第三秒执行一次）
- `README.md` - 说明文档

## 路径配置

**重要：** 配置基于以下路径结构：

- **代码库位置：** `/opt/xmmcg/`
- **静态文件：** `/var/www/xmmcg/` （nginx 服务的静态文件和媒体文件）
- **日志文件：** `/var/log/xmmcg/`
- **虚拟环境：** `/opt/xmmcg/.venv/`

## 安装步骤

### 1. 设置脚本执行权限

```bash
# 必须先设置执行权限
sudo chmod +x /opt/xmmcg/scripts/update_phase_linux.sh
```

### 2. 复制配置文件

```bash
sudo cp /opt/xmmcg/scripts/systemd/xmmcg-phase-update.service /etc/systemd/system/
sudo cp /opt/xmmcg/scripts/systemd/xmmcg-phase-update.timer /etc/systemd/system/
```

### 3. 创建日志目录

```bash
sudo mkdir -p /var/log/xmmcg
sudo chown www-data:www-data /var/log/xmmcg
sudo chmod 755 /var/log/xmmcg
```

### 4. 重新加载 systemd

```bash
sudo systemctl daemon-reload
```

### 5. 启用并启动定时器

```bash
sudo systemctl enable xmmcg-phase-update.timer
sudo systemctl start xmmcg-phase-update.timer
```

## 验证和监控

### 检查定时器状态

```bash
# 查看定时器状态
sudo systemctl status xmmcg-phase-update.timer

# 查看所有定时器
sudo systemctl list-timers --all | grep xmmcg
```

### 检查服务执行状态

```bash
# 查看最近的服务执行状态
sudo systemctl status xmmcg-phase-update.service

# 查看详细日志
sudo journalctl -u xmmcg-phase-update.service -f

# 查看应用日志
sudo tail -f /var/log/xmmcg/phase_update_systemd.log
sudo tail -f /var/log/xmmcg/phase_update_systemd_error.log
```

### 手动执行测试

```bash
# 手动执行一次服务
sudo systemctl start xmmcg-phase-update.service

# 查看执行结果
sudo systemctl status xmmcg-phase-update.service
```

## 自定义执行频率

编辑 `/etc/systemd/system/xmmcg-phase-update.timer`：

```ini
[Timer]
# 每 30 分钟
OnCalendar=*:0/30

# 或者：每天特定时间
OnCalendar=*-*-* 08,12,16,20:00:00

# 或者：每 10 分钟
OnCalendar=*:0/10
```

更多时间格式：https://www.freedesktop.org/software/systemd/man/systemd.time.html

## 日志管理

### 日志文件位置

- **systemd 日志：** `/var/log/xmmcg/phase_update_systemd.log`
- **systemd 错误日志：** `/var/log/xmmcg/phase_update_systemd_error.log`
- **应用日志：** `/var/log/xmmcg/phase_update.log`

### 日志轮转

建议设置 logrotate 来管理日志文件大小：

```bash
sudo nano /etc/logrotate.d/xmmcg
```

内容：
```
/var/log/xmmcg/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    su www-data www-data
}
```

## 故障排除

### 常见问题

1. **脚本无执行权限（Permission denied）**
   ```bash
   # 错误：Permission denied at step EXEC
   # 解决：设置执行权限
   sudo chmod +x /opt/xmmcg/scripts/update_phase_linux.sh
   
   # 验证权限
   ls -la /opt/xmmcg/scripts/update_phase_linux.sh
   # 应该显示类似：-rwxr-xr-x
   ```
4
2. **文件所有权问题**
   ```bash
   sudo chown -R www-data:www-data /opt/xmmcg
   sudo chown -R www-data:www-data /var/log/xmmcg
   ```

3. **虚拟环境路径错误**
   - 检查 `/opt/xmmcg/.venv/bin/python` 是否存在
   - 确保虚拟环境已正确安装 Django 和依赖

3. **数据库权限**
   ```bash
   sudo chown www-data:www-data /opt/xmmcg/backend/xmmcg/db.sqlite3
   ```

### 调试命令

```bash
# 停用定时器
sudo systemctl stop xmmcg-phase-update.timer

# 手动运行脚本进行调试
sudo -u www-data /opt/xmmcg/scripts/update_phase_linux.sh

# 检查脚本权限
ls -la /opt/xmmcg/scripts/update_phase_linux.sh
```

## 对比：Cron vs Systemd Timer

| 特性 | Cron | Systemd Timer |
|------|------|---------------|
| 易用性 | 简单 | 稍复杂 |
| 日志 | 需配置 | 自带（journalctl）|
| 精确度 | 分钟级 | 微秒级 |
| 依赖 | 无 | 支持 |
| 错误处理 | 基础 | 高级 |

## 推荐使用场景

- **Cron**: 简单场景，快速部署
- **Systemd Timer**: 生产环境，需要详细日志和错误处理

## 卸载

```bash
sudo systemctl stop xmmcg-phase-update.timer
sudo systemctl disable xmmcg-phase-update.timer
sudo rm /etc/systemd/system/xmmcg-phase-update.service
sudo rm /etc/systemd/system/xmmcg-phase-update.timer
sudo systemctl daemon-reload
```

## 迁移工具

如果你是从旧的 `/var/www/xmmcg-net/` 路径结构迁移过来的，可以使用提供的迁移脚本：

```bash
sudo chmod +x /opt/xmmcg/scripts/migrate_paths.sh
sudo /opt/xmmcg/scripts/migrate_paths.sh
```

# 数据库备份配置

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