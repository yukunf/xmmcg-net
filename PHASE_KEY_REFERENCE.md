# 比赛阶段 phase_key 参考手册

## 📋 官方阶段 ID 列表

| phase_key | 阶段名称 | 功能描述 | 前端限制 |
|-----------|---------|---------|---------|
| `music_submit` | 歌曲提交期 | 音乐人上传原创歌曲 | Songs 页面允许上传 |
| `music_bid` | 歌曲竞标期 | 谱师对歌曲进行竞标 | Songs 页面显示竞标按钮 |
| `music_allocation` | 歌曲分配期 | 系统自动分配歌曲给谱师 | **仅视觉用途，不参与权限判断** |
| `mapping1` | 第一次谱面制作期 | 谱师制作并提交第一阶段谱面 | Charts 页面允许上传 |
| `chart_bid` | 谱面竞标期 | 选手对谱面进行竞标 | Charts 页面显示竞标按钮 |
| `mapping2` | 第二次谱面制作期 | 中标选手完成最终谱面 | Charts 页面允许上传 |
| `eval` | 互评期 | 选手互相评价作品 | Eval 页面开放 |

---

## 🔍 前端权限控制逻辑

### Songs.vue

```javascript
// ✅ 歌曲上传
isMusicSubmissionPhase() {
  return phases.some(p => p.phase_key === 'music_submit' && p.is_active)
}

// ✅ 歌曲竞标
isSongBiddingPhase() {
  return phases.some(p => p.phase_key === 'music_bid' && p.is_active)
}
```

### Charts.vue

```javascript
// ✅ 谱面上传 (mapping1 或 mapping2)
isChartingPhase() {
  return phase.is_active && (
    phase.phase_key === 'mapping1' || 
    phase.phase_key === 'mapping2'
  )
}

// ✅ 谱面竞标
isChartBiddingPhase() {
  return phase.is_active && phase.phase_key === 'chart_bid'
}
```

---

## ⚠️ 重要说明

1. **`music_allocation` 不参与权限判断**
   - 仅用于前端时间轴显示
   - 不控制任何功能的开关
   - 可以忽略其 `is_active` 状态

2. **严格匹配 phase_key**
   - 不使用 `includes()` 等模糊匹配
   - 每个功能只绑定特定的 phase_key
   - 避免意外误匹配

3. **前后端一致性**
   - 前端使用 phase_key 控制 UI 显示
   - 后端使用 is_active 验证权限
   - 定时任务自动更新 is_active 状态

---

## 🧪 测试阶段创建示例

使用 `create_test_phases.py` 创建测试数据：

```python
test_phases = [
    {
        'name': '歌曲提交期',
        'phase_key': 'music_submit',
        'start_time': now - timedelta(hours=2),
        'end_time': now - timedelta(hours=1),
        'is_active': True,
    },
    {
        'name': '歌曲竞标期',
        'phase_key': 'music_bid',
        'start_time': now - timedelta(minutes=30),
        'end_time': now + timedelta(minutes=30),
        'is_active': True,
    },
    {
        'name': '歌曲分配期（仅视觉）',
        'phase_key': 'music_allocation',
        'start_time': now + timedelta(minutes=35),
        'end_time': now + timedelta(minutes=55),
        'is_active': True,  # 不影响功能
    },
    {
        'name': '第一次谱面制作期',
        'phase_key': 'mapping1',
        'start_time': now + timedelta(hours=1),
        'end_time': now + timedelta(hours=3),
        'is_active': True,
    },
    {
        'name': '谱面竞标期',
        'phase_key': 'chart_bid',
        'start_time': now + timedelta(hours=4),
        'end_time': now + timedelta(hours=6),
        'is_active': True,
    },
    {
        'name': '第二次谱面制作期',
        'phase_key': 'mapping2',
        'start_time': now + timedelta(hours=7),
        'end_time': now + timedelta(hours=9),
        'is_active': True,
    },
    {
        'name': '互评期',
        'phase_key': 'eval',
        'start_time': now + timedelta(hours=10),
        'end_time': now + timedelta(hours=13),
        'is_active': True,
    },
]
```

---

## 📊 阶段流程图

```
1. music_submit (歌曲提交)
         ↓
2. music_bid (歌曲竞标)
         ↓
3. music_allocation (分配 - 仅视觉)
         ↓
4. mapping1 (第一次制谱)
         ↓
5. chart_bid (谱面竞标)
         ↓
6. mapping2 (第二次制谱)
         ↓
7. eval (互评)
```

---

## 🔧 维护指南

### 添加新阶段

1. 在数据库中创建 `CompetitionPhase` 记录
2. 设置正确的 `phase_key`（遵循命名规范）
3. 在前端添加对应的阶段检查函数
4. 更新此文档

### 修改现有阶段

1. ⚠️ **不要修改 phase_key** - 前端代码依赖此值
2. 可以修改 `name`, `description`, `start_time`, `end_time`
3. 运行 `update_phase_status` 更新 `is_active` 状态

### 调试阶段问题

```bash
# 查看当前阶段状态
cd backend/xmmcg
python verify_phase_status.py

# 手动更新 is_active
python manage.py update_phase_status

# 测试 dry-run
python manage.py update_phase_status --dry-run
```

---

**最后更新**: 2026-01-30  
**维护者**: 开发团队
