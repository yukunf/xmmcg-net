# 竞标系统快速开始指南

## 1. 系统已准备好使用 ✓

竞标系统已完全实现并测试通过。所有必要的数据库迁移已应用。

## 2. API 快速参考

### Admin 操作

#### 创建竞标轮次
```bash
curl -X POST http://localhost:8000/api/bidding-rounds/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <csrf_token>" \
  -d '{
    "name": "January 2025 Bidding"
  }'
```

#### 执行竞标分配
```bash
curl -X POST http://localhost:8000/api/bids/allocate/ \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <csrf_token>" \
  -d '{
    "round_id": 1
  }'
```

### 用户操作

#### 上传歌曲（支持多首，限制: 2首）
```bash
curl -X POST http://localhost:8000/api/songs/ \
  -H "Authorization: Bearer <user_token>" \
  -H "X-CSRFToken: <csrf_token>" \
  -F "title=My Song" \
  -F "audio_file=@song.mp3" \
  -F "cover_image=@cover.jpg"
```

#### 创建竞标（限制: 每轮最多 5 个）
```bash
curl -X POST http://localhost:8000/api/bids/ \
  -H "Authorization: Bearer <user_token>" \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <csrf_token>" \
  -d '{
    "song_id": 1,
    "amount": 500
  }'
```

#### 查看我的竞标
```bash
curl http://localhost:8000/api/bids/ \
  -H "Authorization: Bearer <user_token>"
```

#### 查看分配结果
```bash
curl http://localhost:8000/api/bid-results/ \
  -H "Authorization: Bearer <user_token>"
```

## 3. 配置调整

### 修改竞标限制

编辑 `songs/models.py`，第 6-11 行：

```python
# 每个用户可上传的歌曲数量限制
MAX_SONGS_PER_USER = 2    # <- 改为需要的值

# 每个用户可以竞标的歌曲数量限制
MAX_BIDS_PER_USER = 5     # <- 改为需要的值
```

**修改后不需要重新迁移，直接重启服务器即可生效。**

## 4. 快速验证

验证竞标系统是否正常工作：

```bash
cd backend/xmmcg
python verify_bidding.py
```

应该看到：
```
✓ Song 模型正常
✓ BiddingRound 模型正常
✓ Bid 模型正常
✓ BidResult 模型正常
✓ 创建竞标完成
✓ 竞标分配完成
✓ 竞标系统验证完成，所有功能正常！
```

## 5. 完整竞标流程示例

### 场景：3 个用户竞标 2 首歌曲

#### 准备阶段

```bash
# 1. 创建竞标轮次（Admin）
POST /api/bidding-rounds/
{
    "name": "Weekly Bidding #1"
}
# 响应: { "id": 1, "status": "active" }

# 2. 用户1、2、3 各上传 1 首歌曲
POST /api/songs/
# 用户1 上传 "Song A"  (ID: 1)
# 用户2 上传 "Song B"  (ID: 2)
# 用户3 上传 "Song C"  (ID: 3)
```

#### 竞标阶段

```bash
# 用户4 对 Song A 竞标 800 代币
POST /api/bids/
{
    "song_id": 1,
    "amount": 800
}

# 用户5 对 Song A 竞标 600 代币
POST /api/bids/
{
    "song_id": 1,
    "amount": 600
}

# 用户5 对 Song B 竞标 700 代币
POST /api/bids/
{
    "song_id": 2,
    "amount": 700
}

# 用户4 对 Song B 竞标 500 代币
POST /api/bids/
{
    "song_id": 2,
    "amount": 500
}
```

#### 分配阶段

```bash
# Admin 执行分配
POST /api/bids/allocate/
{
    "round_id": 1
}

# 响应:
{
    "success": true,
    "statistics": {
        "total_songs": 3,
        "allocated_songs": 3,
        "winners": 2,
        "total_bidders": 2
    }
}
```

#### 分配结果

```
Song A: 用户4 中标 (800代币) - 最高出价
        用户5 的竞标被 drop

Song B: 用户5 中标 (700代币) - 最高出价
        用户4 的竞标被 drop

Song C: 无人竞标 - 未分配
```

## 6. 关键数据结构

### 竞标轮次状态流转

```
pending (待开始)
    ↓
active (进行中) ← 用户创建竞标
    ↓
completed (已完成) ← Admin 执行分配
```

### 竞标结果类型

- `'win'`: 用户通过竞标获得歌曲（有出价金额）
- `'random'`: 用户未中标，被随机分配歌曲（出价 = 0）

## 7. 常见问题

**Q: 用户可以对同一歌曲多次竞标吗？**
A: 不可以。系统通过数据库约束防止重复竞标。

**Q: 可以修改已创建的竞标吗？**
A: 不可以。需要删除后重新创建（待实现）。

**Q: 分配后，用户的代币会自动扣除吗？**
A: 当前系统仅记录分配结果。代币扣除需要由其他业务逻辑处理。

**Q: 如何修改限制？**
A: 编辑 `songs/models.py` 中的常量，重启服务器即可。

**Q: 一个用户可以上传多首歌曲吗？**
A: 可以的！当前限制是 2 首，可通过修改 `MAX_SONGS_PER_USER` 调整。

## 8. API 状态码

| 代码 | 含义 |
|------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求错误（验证失败） |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |

## 9. 错误处理示例

```javascript
// JavaScript 错误处理示例
async function placeBid(songId, amount) {
    try {
        const response = await fetch('/api/bids/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ song_id: songId, amount: amount })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message);
        }

        return await response.json();
    } catch (error) {
        console.error('竞标失败:', error.message);
        // 可能的错误:
        // - 竞标数量超限
        // - 代币余额不足
        // - 用户已对该歌曲竞标过
        // - 没有活跃的竞标轮次
    }
}
```

## 10. 数据库表概览

| 表 | 用途 | 关键字段 |
|----|------|---------|
| songs_song | 歌曲 | user_id, title, audio_hash |
| songs_biddingrou nd | 竞标轮次 | name, status |
| songs_bid | 竞标记录 | user_id, song_id, amount, is_dropped |
| songs_bidresult | 分配结果 | user_id, song_id, bid_amount, allocation_type |

## 11. 下一步

### 立即可用
- ✓ 完整的 API 端点
- ✓ 自动分配算法
- ✓ 权限控制

### 推荐添加
- [ ] 竞标撤销功能
- [ ] 实时竞标排名（WebSocket）
- [ ] 竞标计时器
- [ ] 代币扣款集成

### 文档参考
- [完整系统指南](BIDDING_SYSTEM_GUIDE.md)
- [实现总结](BIDDING_IMPLEMENTATION_SUMMARY.md)

---

**系统已准备好投入使用！** 🚀

有任何问题或需要调整，请参考完整文档或修改配置常量。
