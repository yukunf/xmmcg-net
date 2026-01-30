# 竞标系统权限控制改进总结

## 🎯 改进目标

将竞标系统的权限控制从**时间检查**改为**依赖 `is_active` 状态**，通过定时任务自动更新状态，实现更清晰、更可靠的权限管理。

---

## ✅ 完成的改进

### 1. **创建定时任务管理命令**

**文件：** `backend/xmmcg/songs/management/commands/update_phase_status.py`

**功能：**
- 根据当前时间和阶段的 `start_time`、`end_time` 自动更新 `is_active` 字段
- 支持 `--dry-run` 参数预览变更而不实际修改数据库
- 详细的日志输出，便于监控和调试

**使用示例：**
```bash
# 实际更新
python manage.py update_phase_status

# 预览模式
python manage.py update_phase_status --dry-run
```

---

### 2. **统一权限检查逻辑**

**文件：** `backend/xmmcg/songs/views.py`

**新增辅助函数：**

#### `get_active_phase_for_bidding()`
获取可用于竞标的活跃阶段，支持：
- 指定阶段 ID 或自动查找当前活跃阶段
- 管理员绕过 `is_active` 检查
- 普通用户严格依赖 `is_active=True`

#### `validate_phase_for_submission()`
验证阶段是否可用于提交竞标：
- 管理员可以绕过所有检查
- 普通用户必须在 `is_active=True` 的阶段才能提交

---

### 3. **修改竞标创建逻辑**

**改进点：**
- ❌ **移除**：基于时间范围的权限检查（`start_time <= now <= end_time`）
- ✅ **改用**：严格依赖 `is_active` 字段
- ✅ **保留**：管理员操作不受限制（可以操作任何阶段）

**Before（旧逻辑）：**
```python
# 普通用户和管理员都检查时间范围
active_phase = CompetitionPhase.objects.filter(
    is_active=True,
    start_time__lte=now,
    end_time__gte=now  # 时间检查
).first()
```

**After（新逻辑）：**
```python
# 使用辅助函数，管理员可绕过 is_active
phase = get_active_phase_for_bidding(
    bid_type='song',
    phase_id=round_id,
    is_admin=request.user.is_staff  # 管理员标识
)

# 验证权限（管理员自动通过）
is_valid, error_message = validate_phase_for_submission(phase, is_admin)
```

---

## 🔄 业务逻辑流程

### **普通用户提交竞标**

1. 前端调用 `POST /api/bids/` 并传入 `round_id`（可选）
2. 后端使用 `get_active_phase_for_bidding()` 获取阶段
   - ✅ `is_active=True` → 允许继续
   - ❌ `is_active=False` → 返回错误："该竞标轮次未开放或已结束"
3. 调用 `BiddingService.create_bid()` 创建竞标

### **管理员操作**

1. 管理员可以通过任何 `round_id` 提交竞标（即使 `is_active=False`）
2. 管理员可以在后台分配竞标，不受阶段状态限制

### **定时任务自动更新**

1. 每小时（或自定义频率）执行 `update_phase_status`
2. 根据当前时间检查所有阶段：
   - `start_time <= now <= end_time` → 设置 `is_active=True`
   - 其他情况 → 设置 `is_active=False`
3. 更新数据库并记录日志

---

## 📋 部署检查清单

### 开发环境

- [ ] 测试命令：`python manage.py update_phase_status --dry-run`
- [ ] 验证普通用户在 `is_active=False` 时无法提交竞标
- [ ] 验证管理员可以绕过 `is_active` 限制

### 生产环境

- [ ] 配置 Windows 任务计划程序（或 Cron/Celery）
- [ ] 设置执行频率（建议每小时）
- [ ] 配置日志路径和自动清理
- [ ] 设置失败重试机制
- [ ] 配置阶段切换前的通知（可选）

---

## 🚀 如何设置定时任务

### 方案 A：Windows 任务计划程序

```powershell
# 快速创建（管理员权限）
schtasks /create /tn "XMMCG-PhaseUpdate" ^
  /tr "C:\Users\fengy\xmmcg-net\scripts\update_phase.bat" ^
  /sc hourly /st 00:00
```

### 方案 B：手动配置

1. 打开任务计划程序（`taskschd.msc`）
2. 创建基本任务："XMMCG Phase Status Update"
3. 触发器：每天，重复间隔 1 小时
4. 操作：执行 `scripts/update_phase.bat`

**详细说明：** 见 [PHASE_STATUS_UPDATE_GUIDE.md](../PHASE_STATUS_UPDATE_GUIDE.md)

---

## 🔍 测试验证

### 测试场景 1：阶段自动激活

```python
# 1. 创建一个即将开始的阶段（1分钟后开始）
phase = CompetitionPhase.objects.create(
    name="测试阶段",
    phase_key="test_bidding",
    start_time=timezone.now() + timedelta(minutes=1),
    end_time=timezone.now() + timedelta(hours=1),
    is_active=False  # 初始状态未激活
)

# 2. 等待 1 分钟，执行命令
python manage.py update_phase_status

# 3. 验证 is_active 已变为 True
phase.refresh_from_db()
assert phase.is_active == True
```

### 测试场景 2：普通用户被阻止

```python
# 假设阶段已过期（is_active=False）
response = client.post('/api/bids/', {
    'song_id': 1,
    'amount': 100,
    'round_id': expired_phase.id
})

# 应该返回 400 错误
assert response.status_code == 400
assert '该竞标轮次未开放或已结束' in response.data['message']
```

### 测试场景 3：管理员绕过限制

```python
# 管理员可以在过期阶段提交竞标
admin_client = APIClient()
admin_client.force_authenticate(user=admin_user)

response = admin_client.post('/api/bids/', {
    'song_id': 1,
    'amount': 100,
    'round_id': expired_phase.id
})

# 应该成功
assert response.status_code == 201
```

---

## 📊 改进对比

| 项目 | 改进前 | 改进后 |
|------|--------|--------|
| **权限判断** | 时间范围检查 | `is_active` 状态 |
| **状态更新** | 手动 | 自动定时更新 |
| **管理员权限** | 受时间限制 | 可绕过限制 |
| **一致性** | 多处不同逻辑 | 统一辅助函数 |
| **可维护性** | 低（分散） | 高（集中） |

---

## 🎓 关键优势

1. **清晰的权限模型**
   - `is_active` 成为唯一权限来源
   - 不再需要同时检查时间和状态

2. **灵活的管理员操作**
   - 管理员可以操作历史阶段
   - 便于数据修正和特殊情况处理

3. **自动化维护**
   - 定时任务自动更新状态
   - 减少人工干预

4. **更好的可测试性**
   - 权限逻辑集中在辅助函数中
   - 易于编写单元测试

---

## ⚠️ 注意事项

1. **定时任务必须正常运行**
   - 如果定时任务失败，`is_active` 可能不会及时更新
   - 建议配置监控和告警

2. **时区一致性**
   - 确保 Django `TIME_ZONE` 设置正确
   - 定时任务和数据库时间应保持一致

3. **阶段时间配置**
   - 阶段的 `start_time` 和 `end_time` 必须准确
   - 避免重叠或间隙

4. **向后兼容**
   - 辅助函数支持旧的调用方式
   - 可以逐步迁移代码

---

## 📚 相关文件

- **核心逻辑：** `backend/xmmcg/songs/views.py`
- **管理命令：** `backend/xmmcg/songs/management/commands/update_phase_status.py`
- **批处理脚本：** `scripts/update_phase.bat`
- **部署指南：** `PHASE_STATUS_UPDATE_GUIDE.md`

---

## 🎯 下一步建议

1. **监控系统**
   - 配置定时任务失败告警
   - 记录 `is_active` 状态变更历史

2. **前端优化**
   - 前端可以缓存 `is_active` 状态
   - 定期轮询或使用 WebSocket 实时更新

3. **测试覆盖**
   - 添加自动化测试验证权限逻辑
   - 测试定时任务执行结果

4. **文档完善**
   - 在 API 文档中说明权限模型
   - 提供常见问题解答

---

**改进完成！** 🎉

现在竞标系统拥有更清晰、更可靠的权限控制机制。
