# Systemd Timer 部署指南

## 什么是 Systemd Timer？

Systemd Timer 是 Cron 的现代替代方案，具有以下优势：
- 更好的日志集成（journalctl）
- 更精确的时间控制
- 依赖管理
- 系统化的服务管理
- 更好的错误处理

## 部署步骤

### 1. 复制 Service 和 Timer 文件

```bash
# 复制文件到 systemd 目录
sudo cp /var/www/xmmcg-net/scripts/systemd/*.service /etc/systemd/system/
sudo cp /var/www/xmmcg-net/scripts/systemd/*.timer /etc/systemd/system/

# 设置正确的权限
sudo chmod 644 /etc/systemd/system/xmmcg-phase-update.*
```

### 2. 重新加载 Systemd 配置

```bash
sudo systemctl daemon-reload
```

### 3. 启用并启动 Timer

```bash
# 启用 timer（开机自启）
sudo systemctl enable xmmcg-phase-update.timer

# 启动 timer
sudo systemctl start xmmcg-phase-update.timer
```

### 4. 验证状态

```bash
# 查看 timer 状态
sudo systemctl status xmmcg-phase-update.timer

# 查看所有 timers
sudo systemctl list-timers

# 查看 service 状态
sudo systemctl status xmmcg-phase-update.service
```

## 常用命令

```bash
# 手动触发一次执行
sudo systemctl start xmmcg-phase-update.service

# 查看执行日志
sudo journalctl -u xmmcg-phase-update.service -f

# 查看最近 50 条日志
sudo journalctl -u xmmcg-phase-update.service -n 50

# 停止 timer
sudo systemctl stop xmmcg-phase-update.timer

# 禁用 timer
sudo systemctl disable xmmcg-phase-update.timer
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
