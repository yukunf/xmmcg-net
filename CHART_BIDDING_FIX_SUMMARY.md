# 谱面竞标轮次读取问题修复总结

## 问题描述

前端在谱面竞标页面会错误地显示已经结束的歌曲竞标轮次数据，而不是当前活跃的谱面竞标轮次。

## 根本原因

数据库验证结果：
- 轮次1：`song` 类型（歌曲竞标），状态 `completed`，有75个竞标
- 轮次2：`chart` 类型（谱面竞标），状态 `active`，有0个竞标

**问题根源**：
1. 前端的 `loadMyChartBids()` 函数找到了活跃的谱面竞标轮次（轮次2）
2. 调用 `getMyBids(2)` 传递轮次ID给后端
3. 后端的 `user_bids_root` 函数硬编码了 `bidding_type='song'`：
   ```python
   round_obj = BiddingRound.objects.get(id=round_id, bidding_type='song')
   ```
4. 由于轮次2是 `chart` 类型，查询失败，返回错误或混乱的数据

## 解决方案

### 后端修复 (`backend/xmmcg/songs/views.py`)

1. **添加竞标类型参数支持**：
   - API现在接受 `bidding_type` 查询参数（默认为 `'song'`）
   - 移除了硬编码的 `bidding_type='song'` 限制

2. **改进轮次验证逻辑**：
   ```python
   # 修复前
   round_obj = BiddingRound.objects.get(id=round_id, bidding_type='song')
   
   # 修复后
   round_obj = BiddingRound.objects.get(id=round_id)
   if round_obj.bidding_type != bidding_type:
       # 返回明确的错误信息，避免混乱
   ```

3. **增强响应信息**：
   - 在响应中包含 `bidding_type` 字段
   - 提供明确的错误消息说明类型不匹配

### 前端修复 (`front/src/api/index.js` 和 `Charts.vue`)

1. **API方法增强**：
   ```javascript
   // 修复前
   export const getMyBids = async (roundId) => { ... }
   
   // 修复后
   export const getMyBids = async (roundId, biddingType = 'song') => {
     const params = {}
     if (roundId) params.round_id = roundId
     if (biddingType) params.bidding_type = biddingType
     // ...
   }
   ```

2. **调用方式修正**：
   ```javascript
   // 修复前
   const res = await getMyBids(targetChartRound.id)
   
   // 修复后  
   const res = await getMyBids(targetChartRound.id, 'chart')
   ```

## 测试验证

### API测试结果
- ✅ `GET /api/songs/bids/?round_id=2&bidding_type=chart` 返回 200
- ✅ 返回正确的空竞标列表（因为还没有人竞标谱面）
- ✅ 轮次信息正确显示为谱面竞标类型

### 数据库验证
- ✅ 轮次2确实是 `chart` 类型，状态 `active`
- ✅ 没有混入歌曲竞标的数据
- ✅ 轮次类型正确区分

## 预期效果

修复后，用户在谱面竞标页面将看到：
1. **正确的轮次信息**：显示活跃的谱面竞标轮次（轮次2）
2. **准确的竞标数据**：只显示谱面竞标，不会混入歌曲竞标
3. **清晰的状态**：当前没有谱面竞标时显示空列表，而不是错误数据

## 修复文件

### 后端
- `backend/xmmcg/songs/views.py` - 修复 `user_bids_root` 函数

### 前端  
- `front/src/api/index.js` - 增强 `getMyBids` 方法
- `front/src/views/Charts.vue` - 修正API调用方式

---

**修复完成时间**: 2026-02-04  
**影响范围**: 谱面竞标功能  
**风险评估**: 低风险，向后兼容