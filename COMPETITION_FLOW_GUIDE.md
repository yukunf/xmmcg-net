# 比赛流程与阶段统计说明

## 完整比赛流程

### 阶段 1：第一轮竞标（Song Bidding Round 1）
**phase_key**: `bidding_round1`

**流程**：
1. 用户上传歌曲到平台
2. 用户使用代币竞标喜欢的歌曲
3. 系统分配：高出价者中标，未中标的随机分配

**统计数据**：
- 参赛人数：所有参与竞标的用户数
- **歌曲数**：平台上传的歌曲总数

---

### 阶段 2：第一部分制谱（Mapping Phase 1）
**phase_key**: `mapping_phase_1` 或 `charting_1`

**流程**：
1. 中标用户获得歌曲制作权
2. 用户制作谱面的前半部分（半成品）
3. 提交第一部分谱面（`is_part_one=True`）

**统计数据**：
- 参赛人数：所有参与竞标的用户数
- **谱面数（第一部分）**：已提交的第一部分谱面数量

**相关模型**：
```python
Chart.objects.filter(is_part_one=True).count()
```

---

### 阶段 3：第二轮竞标（Chart Bidding Round 2）
**phase_key**: `bidding_round2`

**流程**：
1. 所有用户竞标半成品谱面（第一部分谱面）
2. 用户使用代币竞标想要续写的谱面
3. 系统分配：高出价者获得续写权

**统计数据**：
- 参赛人数：所有参与竞标的用户数
- **歌曲数**：可竞标的歌曲/谱面数量（第一部分谱面数）

**业务逻辑**：
- 竞标对象是第一部分谱面，不是新歌曲
- 中标者获得谱面续写权

---

### 阶段 4：第二部分制谱（Mapping Phase 2）
**phase_key**: `mapping_phase_2` 或 `charting_2`

**流程**：
1. 第二轮中标用户获得谱面续写权
2. 用户完成谱面的后半部分
3. 提交第二部分谱面（`is_part_one=False`）

**统计数据**：
- 参赛人数：所有参与竞标的用户数
- **谱面数（第二部分）**：已提交的第二部分谱面数量

**相关模型**：
```python
Chart.objects.filter(is_part_one=False).count()
```

---

### 阶段 5：互评阶段（Peer Review）
**phase_key**: `peer_review`

**流程**：
1. 所有用户对完整谱面进行评分
2. 每人评分 8 个谱面（`PEER_REVIEW_TASKS_PER_USER = 8`）
3. 评分范围：0-50 分

**统计数据**：
- 参赛人数：所有参与竞标的用户数
- **待评谱面数**：已提交等待评分的谱面数

**相关模型**：
```python
Chart.objects.filter(status='submitted').count()
```

---

## API 响应说明

### GET /api/songs/status/

**响应格式**：
```json
{
  "currentRound": "第一轮竞标",
  "status": "active",
  "statusText": "进行中",
  "participants": 25,
  "submissions": 30,
  "submissionsLabel": "歌曲数",
  "phaseKey": "bidding_round1",
  "startTime": "2026-01-20T09:00:00Z",
  "endTime": "2026-01-22T17:00:00Z"
}
```

**字段说明**：
- `currentRound`: 当前阶段名称
- `status`: 阶段状态（pending/active/completed）
- `statusText`: 状态中文描述
- `participants`: 参赛总人数（全局统计）
- `submissions`: 提交作品数（根据阶段类型动态计算）
- `submissionsLabel`: **新增** - 提交作品数的标签（动态变化）
  - 竞标阶段：`"歌曲数"`
  - 制谱阶段：`"谱面数"`
  - 互评阶段：`"待评谱面数"`
- `phaseKey`: 阶段标识符
- `startTime`/`endTime`: 阶段时间范围

---

## 统计逻辑总结

| 阶段 | phase_key 包含 | submissions 统计 | submissionsLabel |
|------|---------------|-----------------|------------------|
| 第一轮竞标 | `bidding` | `Song.objects.count()` | 歌曲数 |
| 第一部分制谱 | `mapping` 或 `chart` | `Chart.objects.count()` | 谱面数 |
| 第二轮竞标 | `bidding` | `Song.objects.count()` | 歌曲数 |
| 第二部分制谱 | `mapping` 或 `chart` | `Chart.objects.count()` | 谱面数 |
| 互评阶段 | `peer_review` 或 `review` | `Chart.objects.filter(status='submitted').count()` | 待评谱面数 |

---

## 前端展示逻辑

**Home.vue** 中的比赛状态卡片会根据 `submissionsLabel` 动态显示：

```vue
<div class="status-label">{{ competitionStatus.submissionsLabel || '提交作品数' }}</div>
<div class="status-value">{{ competitionStatus.submissions || 0 }}</div>
```

**示例显示**：
- 第一轮竞标期间：`歌曲数: 30`
- 制谱期间：`谱面数: 15`
- 互评期间：`待评谱面数: 15`

---

## 数据模型关系

### Song（歌曲）
- 用户上传的音频文件
- 第一轮竞标的对象

### BidResult（竞标结果）
- 记录哪个用户中标了哪首歌曲
- 关联到 Song 和 User

### Chart（谱面）
- 用户制作的谱面文件
- 关联到 Song、User、BidResult
- `is_part_one` 字段区分第一/第二部分

### 关系链：
```
Song → BidResult → Chart (is_part_one=True) → 第二轮竞标 → Chart (is_part_one=False)
```

---

## 管理员操作指南

### 创建完整比赛流程

1. **创建第一轮竞标阶段**
   - 进入后台 `/admin/songs/competitionphase/`
   - 添加阶段：名称="第一轮竞标"，phase_key="bidding_round1"
   - 设置时间范围

2. **创建第一部分制谱阶段**
   - 添加阶段：名称="第一部分制谱"，phase_key="mapping_phase_1"
   - 设置时间范围（在第一轮竞标结束后开始）

3. **创建第二轮竞标阶段**
   - 添加阶段：名称="第二轮竞标"，phase_key="bidding_round2"
   - 设置时间范围

4. **创建第二部分制谱阶段**
   - 添加阶段：名称="第二部分制谱"，phase_key="mapping_phase_2"
   - 设置时间范围

5. **创建互评阶段**
   - 添加阶段：名称="互评阶段"，phase_key="peer_review"
   - 设置时间范围

### 分配竞标结果

**第一轮竞标后**：
1. 进入 `/admin/songs/biddinground/`
2. 选择对应轮次
3. 执行分配操作（通过 API 或管理命令）

**第二轮竞标后**：
1. 同样执行分配操作
2. 分配对象是第一部分谱面

---

## 注意事项

1. **phase_key 命名规范**：
   - 竞标阶段必须包含 `bidding`
   - 制谱阶段包含 `mapping` 或 `chart`
   - 互评阶段包含 `peer_review` 或 `review`

2. **时间衔接**：
   - 各阶段时间不应重叠
   - 下一阶段应在上一阶段结束后开始

3. **代币管理**：
   - 第一轮竞标消耗代币
   - 第二轮竞标也消耗代币
   - 需要确保用户有足够代币参与两轮

4. **数据一致性**：
   - Chart 必须关联正确的 BidResult
   - 第二部分谱面必须关联第一部分谱面对应的歌曲
