# Debian/Linux 生产环境配置完成总结

## ✅ 已完成的配置

### 1. **时区同步配置**

#### Django 时区设置
- **文件:** `backend/xmmcg/xmmcg/settings.py`
- **配置:**
  ```python
  TIME_ZONE = 'Asia/Shanghai'  # 中国标准时间
  USE_TZ = True                 # 启用时区支持
  LANGUAGE_CODE = 'zh-hans'     # 中文简体
  ```
- **特性:**
  - 支持通过环境变量覆盖：`TIME_ZONE=Asia/Shanghai`
  - 数据库存储 UTC 时间，显示时自动转换为本地时间
  - 定时任务和数据库时间完全同步

#### 系统时区
- 设置为 `Asia/Shanghai`（CST +0800）
- 通过 `timedatectl` 管理
- 与 Django 时区保持一致

---

### 2. **定时任务脚本**

#### 基础更新脚本
- **文件:** `scripts/update_phase_linux.sh`
- **功能:** 
  - 激活虚拟环境
  - 执行 Django 管理命令
  - 记录详细日志
  - 错误处理和退出码

#### 智能频率脚本
- **文件:** `scripts/smart_update_phase.sh`
- **功能:**
  - 动态计算距离下次阶段切换的时间
  - **平时:** 每小时执行 1 次（整点）
  - **切换前 2 小时:** 每 10 分钟执行 1 次
  - 自动调整执行频率，平衡资源和及时性

---

### 3. **定时任务配置方案**

提供了 3 种方案，适应不同需求：

#### 方案 A：Cron - 固定频率
- **配置文件:** `scripts/crontab.example`
- **频率:** 每小时整点
- **适用:** 简单场景，快速部署
- **命令:**
  ```bash
  0 * * * * /var/www/xmmcg-net/scripts/update_phase_linux.sh
  ```

#### 方案 B：Cron - 智能频率（推荐）
- **配置文件:** `scripts/crontab.example`
- **频率:** 平时每小时，切换前每 10 分钟
- **适用:** 生产环境，平衡资源和及时性
- **命令:**
  ```bash
  */10 * * * * /var/www/xmmcg-net/scripts/smart_update_phase.sh
  ```

#### 方案 C：Systemd Timer（现代方案）
- **配置文件:** `scripts/systemd/*.service` 和 `*.timer`
- **频率:** 每小时（可自定义）
- **适用:** 需要详细日志和高级错误处理
- **优势:**
  - 集成 journalctl 日志
  - 微秒级精确度
  - 依赖管理和错误重试

---

### 4. **部署工具**

#### 一键部署脚本
- **文件:** `scripts/deploy_phase_update.sh`
- **功能:**
  - 自动设置系统时区
  - 配置脚本权限
  - 测试 Django 命令
  - 交互式选择定时任务方案
  - 验证部署结果

#### 部署步骤：
```bash
chmod +x /opt/xmmcg/scripts/deploy_phase_update.sh
sudo /opt/xmmcg/scripts/deploy_phase_update.sh
```

---

### 5. **文档**

| 文档 | 用途 |
|------|------|
| `DEPLOYMENT_GUIDE_DEBIAN.md` | 完整部署指南 |
| `scripts/crontab.example` | Cron 配置示例 |
| `scripts/systemd/README.md` | Systemd Timer 指南 |

---

## 📊 方案对比

| 方案 | 频率 | 资源占用 | 及时性 | 复杂度 | 推荐场景 |
|------|------|---------|--------|--------|---------|
| **Cron 固定** | 每小时 | 低 | 中 | 简单 | 小型项目 |
| **Cron 智能** | 动态调整 | 中 | 高 | 中等 | 生产环境（推荐）|
| **Systemd Timer** | 自定义 | 中 | 高 | 较复杂 | 大型企业 |

---

## 🚀 推荐配置（生产环境）

### 系统要求
- Debian 10+ / Ubuntu 20.04+
- Python 3.8+
- Django 4.0+
- 虚拟环境已配置

### 推荐方案：Cron 智能频率

**优势：**
- ✅ 平时低频执行，节省资源（每小时 1 次）
- ✅ 关键时刻高频执行，确保及时性（每 10 分钟）
- ✅ 自动调整，无需人工干预
- ✅ 配置简单，易于维护

**配置命令：**
```bash
# 1. 设置系统时区
sudo timedatectl set-timezone Asia/Shanghai

# 2. 运行部署脚本
cd /var/www/xmmcg-net
chmod +x scripts/deploy_phase_update.sh
sudo scripts/deploy_phase_update.sh

# 3. 选择方案 1（智能频率）

# 4. 验证
crontab -l
tail -f logs/phase_update.log
```

---

## 🔍 验证清单

部署完成后，请逐项验证：

- [ ] 系统时区为 `Asia/Shanghai`
  ```bash
  timedatectl | grep "Time zone"
  ```

- [ ] Django 时区为 `Asia/Shanghai`
  ```bash
  cd backend/xmmcg
  source ../../.venv/bin/activate
  python manage.py shell -c "from django.conf import settings; print(settings.TIME_ZONE)"
  ```

- [ ] 脚本有执行权限
  ```bash
  ls -lh scripts/*.sh
  # 应显示 -rwxr-xr-x
  ```

- [ ] Crontab 已配置
  ```bash
  crontab -l | grep xmmcg
  ```

- [ ] 日志目录可写
  ```bash
  touch logs/test.log && rm logs/test.log
  ```

- [ ] 手动测试成功
  ```bash
  scripts/update_phase_linux.sh
  cat logs/phase_update.log
  ```

- [ ] Cron 服务运行中
  ```bash
  sudo systemctl status cron
  ```

---

## ⚙️ 频率调整说明

### 平时频率：每小时（整点执行）
- 适用于没有即将到来的阶段切换
- 资源占用低
- 延迟最多 1 小时

### 高频模式：每 10 分钟
- 自动触发条件：距离下次切换 < 2 小时
- 确保阶段切换的及时性
- 延迟最多 10 分钟

### 自定义调整

编辑 `scripts/smart_update_phase.sh` 中的阈值：

```bash
# 修改这一行来调整切换到高频模式的时间
if [ "${SECONDS_TO_NEXT}" -lt 7200 ]; then  # 7200秒 = 2小时
    # 改为 3600 则为 1 小时前切换
    # 改为 1800 则为 30 分钟前切换
```

---

## 📝 使用示例

### 场景 1：日常运行

```
时间线：
00:00 - 执行更新（整点）
00:10 - 跳过（非整点）
00:20 - 跳过
...
01:00 - 执行更新（整点）
```

### 场景 2：阶段即将切换

```
假设阶段将在 14:00 切换

时间线：
12:00 - 执行更新（整点，距离 2 小时）
12:10 - 执行更新（高频模式启动）
12:20 - 执行更新
...
13:50 - 执行更新
14:00 - 阶段自动切换
14:10 - 执行更新（验证切换成功）
```

---

## 🛡️ 安全和最佳实践

1. **日志轮转**
   ```bash
   # 添加到 crontab
   0 3 * * 0 tail -n 1000 /var/www/xmmcg-net/logs/phase_update.log > /tmp/phase.tmp && mv /tmp/phase.tmp /var/www/xmmcg-net/logs/phase_update.log
   ```

2. **监控告警**
   - 配置邮件告警（MAILTO in crontab）
   - 使用监控工具（如 Prometheus + Grafana）
   - 定期检查日志

3. **备份和恢复**
   - 定期备份数据库
   - 保留阶段配置的历史版本
   - 测试恢复流程

4. **权限最小化**
   - Cron 任务使用普通用户运行
   - 日志目录权限设置为 755
   - 脚本权限设置为 755

---

## 🎯 后续优化建议

1. **监控集成**
   - 添加 Prometheus metrics
   - 集成 Grafana 仪表盘
   - 配置 AlertManager 告警

2. **高可用**
   - 使用 Redis 分布式锁（避免多实例重复执行）
   - 配置主备服务器
   - 实现优雅降级

3. **性能优化**
   - 缓存阶段状态
   - 批量更新数据库
   - 异步执行非关键任务

4. **自动化测试**
   - 添加集成测试
   - 模拟阶段切换场景
   - 验证时区处理正确性

---

## 📞 故障排查

如遇问题，请参考 `DEPLOYMENT_GUIDE_DEBIAN.md` 中的故障排查章节，或执行：

```bash
# 检查完整状态
cd /var/www/xmmcg-net
./scripts/health_check.sh  # 需要先创建此脚本
```

---

**配置完成！您的系统现在拥有智能的阶段状态管理机制。** 🎉

**关键特性：**
- ✅ 时区完全同步
- ✅ 智能频率调整
- ✅ 自动化维护
- ✅ 生产环境就绪
