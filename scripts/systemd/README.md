# XMMCG Phase Status Update - Systemd 配置

## 概述

这个目录包含了用于自动更新 XMMCG 比赛阶段状态的 systemd 配置文件。

## 文件说明

- `xmmcg-phase-update.service` - systemd 服务单元文件
- `xmmcg-phase-update.timer` - systemd 定时器配置（每小时执行一次）
- `README.md` - 说明文档

## 路径配置

**重要：** 配置基于以下路径结构：

- **代码库位置：** `/opt/xmmcg/`
- **静态文件：** `/var/www/xmmcg/` （nginx 服务的静态文件和媒体文件）
- **日志文件：** `/var/log/xmmcg/`
- **虚拟环境：** `/opt/xmmcg/.venv/`

## 安装步骤

### 1. 复制配置文件

```bash
sudo cp /opt/xmmcg/scripts/systemd/xmmcg-phase-update.service /etc/systemd/system/
sudo cp /opt/xmmcg/scripts/systemd/xmmcg-phase-update.timer /etc/systemd/system/
```

### 2. 创建日志目录

```bash
sudo mkdir -p /var/log/xmmcg
sudo chown www-data:www-data /var/log/xmmcg
sudo chmod 755 /var/log/xmmcg
```

### 3. 重新加载 systemd

```bash
sudo systemctl daemon-reload
```

### 4. 启用并启动定时器

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

1. **权限问题**
   ```bash
   sudo chown -R www-data:www-data /opt/xmmcg
   sudo chown -R www-data:www-data /var/log/xmmcg
   ```

2. **虚拟环境路径错误**
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
