# 谱面提交阶段验证修复

## 🐛 问题描述

### 发现的漏洞
用户提出了一个关键问题：**谱面提交没有阶段验证**

### 问题场景
1. **第一轮竞标（music_bid）**：用户获得歌曲，BidResult 绑定到 `music_bid` 阶段
2. **第一次创作（mapping1）**：用户提交半成品谱面 ✅
3. **第二轮竞标（chart_bid）**：用户竞标半成品，获得新 BidResult，绑定到 `chart_bid` 阶段
4. **第二次创作（mapping2）**：用户提交终稿 ❓

**问题**：
- 如果第一阶段（music_bid）的 `is_active` 变为 `False`，用户是否还能提交谱面？
- 原代码 **没有任何阶段验证**，理论上可以在任何时间提交
- 但这可能导致用户在错误的时间提交谱面

### 安全漏洞
- ✅ **前端有控制**：`isChartingPhase` 检查 `mapping1` 或 `mapping2`
- ❌ **后端无验证**：`submit_chart()` 函数没有阶段检查
- 🔓 **绕过前端**：用户可以直接调用 API 绕过前端限制

---

## ✅ 修复方案

### 修改文件
`backend/xmmcg/songs/views.py` - `submit_chart` 函数

### 新增逻辑
```python
# 阶段验证（管理员可绕过）
if not is_admin:
    now = timezone.now()
    active_mapping_phase = CompetitionPhase.objects.filter(
        phase_key__in=['mapping1', 'mapping2', 'chart_mapping'],
        is_active=True,
        start_time__lte=now,
        end_time__gte=now
    ).first()
    
    if not active_mapping_phase:
        return Response({
            'success': False,
            'message': '当前不在谱面创作阶段,无法提交谱面'
        }, status=status.HTTP_400_BAD_REQUEST)
```

### 验证规则
| 用户类型 | 阶段要求 | 说明 |
|---------|---------|------|
| **管理员** | 无限制 | 可以在任何时间提交（用于测试和数据修正） |
| **普通用户** | `mapping1` 或 `mapping2` 或 `chart_mapping` | 必须在创作阶段且 `is_active=True` |

---

## 🔍 验证清单

### 测试场景

#### 1️⃣ 第一次创作（mapping1 阶段）
- [x] `mapping1` 激活 → ✅ 可以提交半成品
- [x] `mapping1` 未激活 → ❌ 拒绝提交（返回 400）

#### 2️⃣ 第二次创作（mapping2 阶段）
- [x] `mapping2` 激活 → ✅ 可以提交终稿
- [x] `mapping2` 未激活 → ❌ 拒绝提交（返回 400）

#### 3️⃣ 管理员权限
- [x] 任何阶段 → ✅ 管理员可以提交

#### 4️⃣ 安全测试
- [x] 绕过前端直接调用 API → ❌ 后端拒绝（阶段验证生效）

---

## 🎯 设计考量

### 为什么不检查 BidResult 绑定的阶段？

**原因**：
1. **BidResult 绑定的是竞标阶段**（`music_bid`, `chart_bid`），不是创作阶段
2. **创作阶段与竞标阶段分离**：
   - 竞标阶段：`music_bid`, `chart_bid`
   - 创作阶段：`mapping1`, `mapping2`
3. **用户可能延迟提交**：即使竞标阶段结束，创作阶段仍在进行

### 为什么支持三个 phase_key？

```python
phase_key__in=['mapping1', 'mapping2', 'chart_mapping']
```

- `mapping1`：第一次谱面创作（提交半成品）
- `mapping2`：第二次谱面创作（提交终稿）
- `chart_mapping`：兼容旧系统的通用创作阶段

---

## 📊 影响范围

### 受影响的功能
- ✅ 谱面提交 API：`POST /api/charts/{result_id}/submit/`
- ✅ 前后端双重验证：前端禁用按钮 + 后端拒绝请求

### 不受影响的功能
- ✅ 竞标提交：继续使用 `get_active_phase_for_bidding()` 验证
- ✅ 歌曲上传：已有阶段验证逻辑
- ✅ 管理员操作：可以绕过所有阶段检查

---

## 🔒 安全增强

### 修复前
```
前端检查 ✅ → 后端无检查 ❌ → 🔓 安全漏洞
```

### 修复后
```
前端检查 ✅ → 后端验证 ✅ → 🔒 双重保护
```

---

## 📝 相关文档

- [BIDDING_PERMISSION_IMPROVEMENT.md](BIDDING_PERMISSION_IMPROVEMENT.md) - 竞标权限改进
- [FRONTEND_PHASE_CONTROL.md](FRONTEND_PHASE_CONTROL.md) - 前端阶段控制
- [PHASE_KEY_REFERENCE.md](PHASE_KEY_REFERENCE.md) - 阶段 Key 参考
- [PHASE_TEST_GUIDE.md](PHASE_TEST_GUIDE.md) - 阶段测试指南

---

## ✅ 总结

**问题**：谱面提交缺少后端阶段验证，存在安全漏洞

**解决方案**：
1. 添加阶段验证逻辑
2. 支持两个创作阶段（mapping1, mapping2）
3. 管理员可绕过限制
4. 前后端双重保护

**影响**：
- ✅ 提高系统安全性
- ✅ 防止用户在错误时间提交
- ✅ 保持管理员灵活性
- ✅ 与现有系统一致
