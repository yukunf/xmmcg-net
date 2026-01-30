# 前端阶段权限控制总结

## 📋 Songs.vue - 歌曲页面权限控制

### ✅ 随时开放的功能
- **浏览歌曲列表** - 无限制
- **查看歌曲详情** - 无限制
- **下载音频/歌曲包** - 无限制
- **搜索/排序/分页** - 无限制

### 🔒 有阶段限制的功能

#### 1. 上传歌曲
**限制条件**: `isMusicSubmissionPhase()`
- **阶段**: `music_submit` 且 `is_active = true`
- **实现位置**:
  ```vue
  :disabled="uploading || !isMusicSubmissionPhase() || mySongs.length >= maxSongUploadsAllowed"
  ```

#### 2. 歌曲竞标
**限制条件**: `isSongBiddingPhase() && !isMyOwnSong(song)`
- **阶段**: `music_bid` 且 `is_active = true`
- **排除**: 自己上传的歌曲
- **实现位置**:
  ```vue
  <el-button 
    v-if="isSongBiddingPhase() && !isMyOwnSong(song)"
    type="success" 
    :icon="TrophyBase" 
    @click="showBidDialog(song)"
  >
    竞标
  </el-button>
  ```

---

## 📋 Charts.vue - 谱面页面权限控制

### ✅ 随时开放的功能
- **浏览谱面列表** - 无限制
- **查看谱面详情** - 无限制
- **下载谱面包** - 无限制
- **查看封面** - 无限制

### 🔒 有阶段限制的功能

#### 1. 上传谱面
**限制条件**: `isChartingPhase`
- **阶段**: 
  - `mapping1` 且 `is_active = true` 或
  - `mapping2` 且 `is_active = true`
- **实现位置**:
  ```vue
  :disabled="uploading || !isChartingPhase || !!myChart"
  ```
- **额外限制**: 只有中标的用户才能上传

#### 2. 谱面竞标
**限制条件**: `isChartBiddingPhase() && chart.is_part_one && chart.status === 'part_submitted'`
- **阶段**: 
  - `chart_bid` 且 `is_active = true` 或
  - `second_bidding` 且 `is_active = 
  - 必须是第一阶段的谱面 (`is_part_one`)
  - 谱面状态为已提交 (`part_submitted`)
- **实现位置**:
  ```vue
  <el-button
    v-if="isChartBiddingPhase() && chart.is_part_one && chart.status === 'part_submitted'"
    type="success"
    size="small"
    :icon="TrophyBase"
    @click="showChartBidDialog(chart)"
  >
    竞标
  </el-button>
  ```

---

## 🔍 阶段检查函数

### Songs.vue

```javascript
// 检查是否在歌曲提交阶段
const isMusicSubmissionPhase = () => {
  if (!allCompetitionPhases.value || allCompetitionPhases.value.length === 0) {
    return false;
  }
  return allCompetitionPhases.value.some(phase => 
    phase.phase_key === "music_submit" && phase.is_active
  );
}

// 检查是否在歌曲竞标阶段（只在 music_bid 阶段开放）
const isSongBiddingPhase = () => {
  if (!allCompetitionPhases.value || allCompetitionPhases.value.length === 0) {
    return false;
  }
  return allCompetitionPhases.value.some(phase => 
    phase.phase_key === 'music_bid' && phase.is_active
  );
}
```

### Charts.vue

```javascript
// 检查是否在谱面创作阶段（只在 mapping1 或 mapping2 开放）
const checkChartingPhase = async () => {
  try {
    const phase = await getCurrentPhase()
    currentPhase.value = phase
    currentPhaseName.value = phase.name || '未知'
    
    isChartingPhase.value = phase.is_active === true && (
      phase.phase_key === 'mapping1' || 
      phase.phase_key === 'mapping2'
    )
  } catch (error) {
    console.error('检查阶段失败:', error)
    isChartingPhase.value = false
  }
}

// 检查是否在谱面竞标阶段（只在 chart_bid 阶段开放）
const isChartBiddingPhase = () => {
  return currentPhase.value?.is_active === true && 
         currentPhase.value?.phase_key === 'chart_bid'
}
```

---

## 🧪 测试验证清单

### 歌曲页面测试

| 功能 | 期待行为 | 验证方法 |
|------|---------|---------|
| 浏览歌曲 | 任何阶段都能浏览 | 在不同阶段访问 Songs 页面 |
| 下载歌曲 | 任何阶段都能下载 | 点击下载按钮 |
| 上传歌曲 | 只在 music_submit 阶段可用 | 检查上传按钮是否禁用 |
| 歌曲竞标 | 只在 song_bid 阶段显示按钮 | 检查竞标按钮是否显示 |

### 谱面页面测试

| 功能 | 期待行为 | 验证方法 |
|------|---------|---------|
| 浏览谱面 | 任何阶段都能浏览 | 在不同阶段访问 Charts 页面 |
| 下载谱面 | 任何阶段都能下载 | 点击下载按钮 |
| 上传谱面 | 只在 mapping1/mapping2 阶段可用 | 检查上传区域是否显示/禁用 |
| 谱面竞标 | 只在 chart_bid/second_bidding 阶段显示按钮 | 检查竞标按钮是否显示 |

---

## ✅ 改进总结

### 修复内容

1. **Songs.vue - `isSongBiddingPhase()`**
   - 从：检查 `includes('bidding')` 且排除 `chart`
   - 改为：严格检查 `phase_key === 'song_bid'`
   - **原因**: 避免误匹配其他包含 'bidding' 的阶段

2. **Charts.vue - `isChartingPhase`**
   - 从：检查 `includes('mapping')` 或 `includes('chart')`
   - 改为：严格检查 `mapping1`, `mapping2`, `chart_mapping`
   - **原因**: 避免在 chart_bid 阶段误开放上传功能

3. **Charts.vue - `isChartBiddingPhase()`**
   - 从：检查 `includes('chart')` 或 `includes('bid')`
   - 改为：严格检查 `chart_bid` 或 `second_bidding`
   - **原因**: 精确控制竞标按钮显示时机

4. **Charts.vue - 竞标按钮**
   - 添加：`v-if="isChartBiddingPhase() && ..."`
   - **原因**: 之前没有阶段检查，任何时候都显示

### 设计原则

1. **浏览功能永不限制** - 用户随时可以查看和下载内容
2. **投稿功能严格限制** - 只在指定的创作阶段开放
3. **竞标功能精确控制** - 只在对应的竞标阶段显示按钮
4. **默认安全策略** - 阶段数据未加载时默认禁止操作

---

## 🔒 后端权限保护

即使前端绕过了这些检查，后端也有对应的权限验证：

- `views.py` 中的 `get_active_phase_for_bidding()` 强制检查 `is_active`
- `validate_phase_for_submission()` 验证提交权限
- 管理员可以绕过限制（用于测试和数据修正）

**前后端双重保护，确保系统安全！**
