# 竞标系统完整指南

## 概述

竞标系统允许用户对现有歌曲进行竞标，通过代币出价获得歌曲的所有权。系统支持以下功能：

1. **用户可以上传多首歌曲**（限制可调整，当前为 2 首）
2. **用户可以竞标歌曲**（每轮最多 5 个，限制可调整）
3. **Admin 可以开始竞标分配**（按出价从高到低分配）
4. **自动分配**（未中标用户随机分配）

---

## 1. 配置常量

所有可调整的常量定义在 [songs/models.py](songs/models.py#L6-L11)：

```python
# 每个用户可上传的歌曲数量限制
MAX_SONGS_PER_USER = 2

# 每个用户可以竞标的歌曲数量限制
MAX_BIDS_PER_USER = 5
```

要修改这些限制，只需在此文件中更改值即可，系统会自动应用新限制。

---

## 2. 数据模型

### 2.1 Song 模型（修改）

**主要变化**：`user` 字段从 `OneToOneField` 改为 `ForeignKey`，允许用户上传多首歌曲。

```python
class Song(models.Model):
    id = models.AutoField(primary_key=True)
    unique_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # 改为 ForeignKey，允许多首歌曲
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='songs'  # 改为复数
    )
    
    title = models.CharField(max_length=100)
    audio_file = models.FileField(upload_to=get_audio_filename)
    cover_image = models.ImageField(upload_to=get_cover_filename, null=True, blank=True)
    netease_url = models.URLField(null=True, blank=True)
    audio_hash = models.CharField(max_length=64, db_index=True)
    file_size = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 2.2 BiddingRound 模型（新增）

代表一个竞标轮次，用于追踪竞标的生命周期。

```python
class BiddingRound(models.Model):
    STATUS_CHOICES = [
        ('pending', '待开始'),   # 还未开始接收竞标
        ('active', '进行中'),    # 正在接收竞标
        ('completed', '已完成'), # 已完成分配
    ]
    
    name = models.CharField(max_length=100)  # 轮次名称
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
```

### 2.3 Bid 模型（新增）

记录用户对特定歌曲的竞标。

```python
class Bid(models.Model):
    bidding_round = models.ForeignKey(BiddingRound, on_delete=models.CASCADE, related_name='bids')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids')
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='bids')
    
    amount = models.IntegerField()  # 竞标金额
    is_dropped = models.BooleanField(default=False)  # 是否已被drop（歌曲被更高出价者获得）
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # 确保一个用户在同一轮竞标中，对同一歌曲只能出价一次
        unique_together = ('bidding_round', 'user', 'song')
```

### 2.4 BidResult 模型（新增）

记录竞标分配的结果。

```python
class BidResult(models.Model):
    ALLOCATION_TYPE_CHOICES = [
        ('win', '中标'),        # 通过竞标获得
        ('random', '随机分配'), # 未中标但被随机分配
    ]
    
    bidding_round = models.ForeignKey(BiddingRound, on_delete=models.CASCADE, related_name='results')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bid_results')
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='bid_results')
    
    bid_amount = models.IntegerField()  # 最终成交金额
    allocation_type = models.CharField(max_length=20, choices=ALLOCATION_TYPE_CHOICES)
    allocated_at = models.DateTimeField(auto_now_add=True)
```

---

## 3. API 端点

### 3.1 歌曲管理 API

#### 上传歌曲（支持多首）
```
POST /api/songs/

权限：需要认证
请求体：
{
    "title": "My Song Title",
    "audio_file": <audio_file>,
    "cover_image": <image_file> (可选),
    "netease_url": "https://..." (可选)
}

成功响应 (201)：
{
    "success": true,
    "message": "歌曲上传成功",
    "song": { /* song details */ }
}

错误响应 (400)：
{
    "success": false,
    "message": "已达到每个用户最多 2 首歌曲的限制",
    "current_count": 2,
    "limit": 2
}
```

#### 获取我的歌曲列表
```
GET /api/songs/me/

权限：需要认证

成功响应 (200)：
{
    "success": true,
    "count": 2,
    "songs": [
        {
            "id": 1,
            "title": "Song Title",
            "user": { "id": 1, "username": "user1" },
            "cover_url": "...",
            "file_size": 5000000,
            "created_at": "2025-01-16T10:00:00Z"
        },
        ...
    ]
}
```

#### 更新歌曲信息
```
PUT /api/songs/{song_id}/update/
或
PATCH /api/songs/{song_id}/update/

权限：需要认证，且必须是歌曲所有者
请求体：
{
    "title": "New Title",
    "netease_url": "https://..."
}
```

#### 删除歌曲
```
DELETE /api/songs/{song_id}/

权限：需要认证，且必须是歌曲所有者

成功响应 (200)：
{
    "success": true,
    "message": "歌曲已删除",
    "deleted_song": {
        "id": 1,
        "title": "Song Title"
    }
}
```

#### 获取歌曲详情
```
GET /api/songs/detail/{song_id}/

权限：任何人都可以访问（用于竞标前查看）

成功响应 (200)：
{
    "success": true,
    "song": {
        "id": 1,
        "title": "Song Title",
        "user": { "id": 1, "username": "uploader" },
        "audio_url": "...",
        "cover_url": "...",
        "netease_url": "...",
        "file_size": 5000000,
        "created_at": "2025-01-16T10:00:00Z",
        "updated_at": "2025-01-16T10:00:00Z"
    }
}
```

### 3.2 竞标轮次管理 API

#### 列出所有竞标轮次
```
GET /api/bidding-rounds/

权限：任何人

成功响应 (200)：
{
    "success": true,
    "count": 2,
    "rounds": [
        {
            "id": 1,
            "name": "First Bidding Round",
            "status": "completed",
            "status_display": "已完成",
            "created_at": "2025-01-16T09:00:00Z",
            "started_at": "2025-01-16T10:00:00Z",
            "completed_at": "2025-01-16T12:00:00Z",
            "bid_count": 25,
            "result_count": 10
        },
        ...
    ]
}
```

#### 创建竞标轮次
```
POST /api/bidding-rounds/

权限：需要管理员权限
请求体：
{
    "name": "January 2025 Bidding Round"
}

成功响应 (201)：
{
    "success": true,
    "message": "竞标轮次已创建",
    "round": {
        "id": 1,
        "name": "January 2025 Bidding Round",
        "status": "active",
        "created_at": "2025-01-16T10:00:00Z"
    }
}

错误响应 (403)：
{
    "success": false,
    "message": "需要管理员权限"
}
```

### 3.3 竞标 API

#### 获取用户的竞标列表
```
GET /api/bids/

权限：需要认证
查询参数：
  - round_id (可选): 指定竞标轮次，不提供则使用最新的活跃轮次

成功响应 (200)：
{
    "success": true,
    "round": {
        "id": 1,
        "name": "January 2025 Bidding Round",
        "status": "active"
    },
    "bid_count": 3,
    "max_bids": 5,
    "bids": [
        {
            "id": 1,
            "song": {
                "id": 1,
                "title": "Song Title",
                "user": { "id": 2, "username": "uploader" },
                "cover_url": "...",
                "file_size": 5000000,
                "created_at": "2025-01-16T10:00:00Z"
            },
            "amount": 500,
            "is_dropped": false,
            "created_at": "2025-01-16T11:00:00Z"
        },
        ...
    ]
}
```

#### 创建竞标
```
POST /api/bids/

权限：需要认证
请求体：
{
    "song_id": 1,
    "amount": 500,
    "round_id": 1 (可选，不提供则使用最新活跃轮次)
}

成功响应 (201)：
{
    "success": true,
    "message": "竞标已创建",
    "bid": {
        "id": 1,
        "song": { /* song details */ },
        "amount": 500,
        "created_at": "2025-01-16T11:00:00Z"
    }
}

可能的错误：
- 缺少必要字段 (400)
- 歌曲不存在 (404)
- 没有活跃的竞标轮次 (404)
- 竞标数量超限 (400): 已达到 MAX_BIDS_PER_USER
- 代币余额不足 (400)
- 用户已对该歌曲竞标过 (400)
```

### 3.4 竞标分配 API

#### 执行竞标分配（Admin only）
```
POST /api/bids/allocate/

权限：需要管理员权限
请求体（可选）：
{
    "round_id": 1 (可选，不提供则分配最新活跃轮次)
}

成功响应 (200)：
{
    "success": true,
    "message": "竞标分配完成",
    "round": {
        "id": 1,
        "name": "January 2025 Bidding Round",
        "status": "completed"
    },
    "statistics": {
        "status": "success",
        "message": "竞标分配完成",
        "total_songs": 10,
        "allocated_songs": 8,
        "unallocated_songs": 2,
        "winners": 5,
        "total_bidders": 7
    }
}

错误响应 (403)：
{
    "success": false,
    "message": "需要管理员权限"
}

错误响应 (404)：
{
    "success": false,
    "message": "竞标轮次不存在或已结束"
}
```

### 3.5 竞标结果 API

#### 获取用户的竞标结果
```
GET /api/bid-results/

权限：需要认证
查询参数：
  - round_id (可选): 指定竞标轮次，不提供则使用最新的已完成轮次

成功响应 (200)：
{
    "success": true,
    "round": {
        "id": 1,
        "name": "January 2025 Bidding Round",
        "status": "completed",
        "completed_at": "2025-01-16T12:00:00Z"
    },
    "result_count": 2,
    "results": [
        {
            "id": 1,
            "song": {
                "id": 1,
                "title": "Song Title",
                "user": { "id": 2, "username": "uploader" },
                "cover_url": "...",
                "file_size": 5000000,
                "created_at": "2025-01-16T10:00:00Z"
            },
            "bid_amount": 500,
            "allocation_type": "win",
            "allocation_type_display": "中标",
            "allocated_at": "2025-01-16T12:00:00Z"
        },
        {
            "id": 2,
            "song": {
                "id": 3,
                "title": "Another Song",
                "user": { "id": 3, "username": "user2" },
                "cover_url": "...",
                "file_size": 3000000,
                "created_at": "2025-01-16T10:05:00Z"
            },
            "bid_amount": 0,
            "allocation_type": "random",
            "allocation_type_display": "随机分配",
            "allocated_at": "2025-01-16T12:00:00Z"
        }
    ]
}
```

---

## 4. 分配算法详解

当 Admin 调用 `POST /api/bids/allocate/` 时，系统执行以下算法：

### 第一阶段：按出价从高到低分配

1. 获取该轮次的所有有效竞标（未被 drop）
2. 按出价金额从高到低排序（同价格则按竞标时间排序，先来先得）
3. 逐个处理每个竞标：
   - 如果该歌曲还未被分配给任何人，标记该竞标为中标
   - 为获胜者创建 `BidResult` 记录（`allocation_type='win'`）
   - 该歌曲的所有其他竞标标记为 `is_dropped=true`

### 第二阶段：随机分配

1. 识别所有参与竞标的用户
2. 找出未获得任何歌曲的用户
3. 从未被分配的歌曲中随机选择
4. 为这些用户创建 `BidResult` 记录（`allocation_type='random'`，`bid_amount=0`）

### 示例场景

假设有以下场景：

**歌曲**：A, B, C, D, E（共 5 首）

**竞标**：
- 用户1 → A (800代币)
- 用户2 → A (600代币)
- 用户2 → B (700代币)
- 用户3 → B (500代币)
- 用户4 → C (400代币)

**分配流程**：

1. 用户1 的竞标 A (800代币) - 最高 → **用户1 中标获得 A**，用户2 对 A 的竞标被 drop
2. 用户2 的竞标 B (700代币) - 第二高 → **用户2 中标获得 B**，用户3 对 B 的竞标被 drop
3. 用户4 的竞标 C (400代币) → **用户4 中标获得 C**
4. 用户3 未获得任何歌曲 → **从 {D, E} 中随机选择一个**，假设得到 D
5. 歌曲 E 无人竞标 → 保持未分配状态

**最终分配结果**：
- 用户1：A (中标, 800代币)
- 用户2：B (中标, 700代币)
- 用户3：D (随机分配, 0代币)
- 用户4：C (中标, 400代币)
- E：未分配

---

## 5. 业务逻辑服务

[BiddingService](songs/bidding_service.py) 类负责处理所有竞标相关的业务逻辑：

### 主要方法

#### `allocate_bids(bidding_round_id)`
执行完整的竞标分配流程。返回分配统计信息。

```python
result = BiddingService.allocate_bids(round_id=1)
print(result)
# {
#     'status': 'success',
#     'message': '竞标分配完成',
#     'total_songs': 10,
#     'allocated_songs': 8,
#     'unallocated_songs': 2,
#     'winners': 5,
#     'total_bidders': 7
# }
```

#### `create_bid(user, bidding_round, song, amount)`
创建新竞标，包含所有验证逻辑。

```python
try:
    bid = BiddingService.create_bid(
        user=request.user,
        bidding_round=round_obj,
        song=song_obj,
        amount=500
    )
    print(f"竞标成功: {bid.id}")
except ValidationError as e:
    print(f"竞标失败: {e.message}")
```

#### `get_user_bids(user, bidding_round)`
获取用户在指定轮次的所有竞标。

```python
bids = BiddingService.get_user_bids(user=user, bidding_round=round_obj)
for bid in bids:
    print(f"竞标 {bid.song.title}: {bid.amount}代币")
```

#### `get_user_results(user, bidding_round)`
获取用户的分配结果。

```python
results = BiddingService.get_user_results(user=user, bidding_round=round_obj)
for result in results:
    print(f"获得 {result.song.title}: {result.allocation_type}")
```

---

## 6. 使用流程示例

### 场景：完整的竞标流程

#### 步骤 1：用户上传歌曲

```bash
# 用户1、2、3 分别上传歌曲
POST /api/songs/
Authorization: Bearer <token1>

{
    "title": "User1's Amazing Song",
    "audio_file": <file>,
    "cover_image": <file>
}

# 响应: { "success": true, "song": { "id": 1, ... } }
```

#### 步骤 2：Admin 创建竞标轮次

```bash
POST /api/bidding-rounds/
Authorization: Bearer <admin_token>

{
    "name": "January 2025 Bidding Round"
}

# 响应: { "success": true, "round": { "id": 1, "status": "active" } }
```

#### 步骤 3：用户浏览所有歌曲

```bash
GET /api/songs/

# 响应: { "success": true, "count": 3, "results": [...] }
```

#### 步骤 4：用户创建竞标

```bash
# 用户4 对歌曲 1 竞标 500 代币
POST /api/bids/
Authorization: Bearer <token4>

{
    "song_id": 1,
    "amount": 500,
    "round_id": 1
}

# 响应: { "success": true, "bid": { "id": 1, ... } }
```

#### 步骤 5：用户查看自己的竞标

```bash
GET /api/bids/?round_id=1
Authorization: Bearer <token4>

# 响应: { "success": true, "bid_count": 3, "bids": [...] }
```

#### 步骤 6：Admin 执行分配

```bash
POST /api/bids/allocate/
Authorization: Bearer <admin_token>

{
    "round_id": 1
}

# 响应: {
#     "success": true,
#     "statistics": {
#         "total_songs": 3,
#         "allocated_songs": 3,
#         "winners": 3,
#         ...
#     }
# }
```

#### 步骤 7：用户查看分配结果

```bash
GET /api/bid-results/?round_id=1
Authorization: Bearer <token4>

# 响应: {
#     "success": true,
#     "result_count": 1,
#     "results": [
#         {
#             "song": { "id": 1, "title": "...", ... },
#             "bid_amount": 500,
#             "allocation_type": "win"
#         }
#     ]
# }
```

---

## 7. 验证规则

### 创建竞标时的验证

1. **竞标轮次必须是"进行中"状态**
   - 不能对已完成或待开始的轮次创建竞标

2. **用户代币余额必须足够**
   - 竞标金额 ≤ 用户当前代币余额

3. **竞标数量不能超过限制**
   - 当前轮次中，用户未drop的竞标数 < `MAX_BIDS_PER_USER`

4. **不能对同一歌曲重复竞标**
   - 同一用户在同一轮次中，只能对每首歌曲竞标一次
   - 可以通过删除后重新竞标来更新出价（需要实现）

5. **竞标金额必须大于 0**

### 创建歌曲时的验证

1. **用户必须已认证**

2. **歌曲数量不能超过限制**
   - 用户已上传的歌曲数 < `MAX_SONGS_PER_USER`

3. **标题、音频文件必需**
   - 标题长度：1-100 个字符
   - 音频文件大小：< 50MB
   - 支持的格式：mp3, wav, flac, m4a

---

## 8. 常见问题

### Q: 用户可以多次竞标同一首歌曲吗？
**A**: 不可以。系统在数据库层通过 `unique_together` 约束确保一个用户在同一轮竞标中，对每首歌曲只能出价一次。如果用户想更新出价，需要先"取消"竞标（待实现），然后重新竞标。

### Q: 如果竞标轮次进行中，用户可以删除自己的歌曲吗？
**A**: 可以。系统在 Song 模型中使用了 `on_delete=models.CASCADE`，删除歌曲时会级联删除所有相关的竞标记录。

### Q: 分配后，是否会扣除用户的代币？
**A**: 当前系统仅记录分配结果，暂未实现自动扣除代币。这通常需要由其他业务逻辑（如支付系统）来处理。

### Q: 如果一首歌曲没有任何竞标，会发生什么？
**A**: 该歌曲在分配时会被列为"未分配"。系统不会自动为其分配给任何用户。

### Q: 用户的随机分配是真随机吗？
**A**: 是的。系统使用 Python 的 `random.choice()` 从未分配的歌曲中随机选择。

---

## 9. 数据库迁移

所有模型更改已通过迁移应用：

```bash
$ python manage.py makemigrations songs
$ python manage.py migrate
```

迁移文件：[songs/migrations/0002_biddinground_alter_song_user_bid_bidresult.py](songs/migrations/0002_biddinground_alter_song_user_bid_bidresult.py)

---

## 10. 前端集成建议

### 获取活跃竞标轮次

```javascript
async function getActiveBiddingRound() {
    const res = await fetch('/api/bidding-rounds/');
    const data = await res.json();
    const activeRound = data.rounds.find(r => r.status === 'active');
    return activeRound;
}
```

### 创建竞标

```javascript
async function placeBid(songId, amount, token) {
    const res = await fetch('/api/bids/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            song_id: songId,
            amount: amount
        })
    });
    
    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.message);
    }
    
    return await res.json();
}
```

### 查看竞标结果

```javascript
async function getBiddingResults(token) {
    const res = await fetch('/api/bid-results/', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    
    const data = await res.json();
    return data.results;
}
```

---

## 11. 性能注意事项

1. **批量竞标优化**：当用户创建大量竞标时，可以使用 `bulk_create` 进行批量插入（需要修改代码）。

2. **分配算法性能**：
   - 获取竞标：O(n)，其中 n 是竞标数
   - 排序：O(n log n)
   - 分配：O(n + m)，其中 m 是歌曲数
   - 总复杂度：O(n log n + n + m) ≈ O(n log n)

3. **数据库查询优化**：
   - 使用 `select_related()` 和 `prefetch_related()` 减少查询数
   - 给频繁查询的字段添加索引

4. **缓存建议**：
   - 缓存竞标轮次列表（使用 Redis）
   - 缓存用户的竞标列表

---

## 12. 安全考虑

1. **权限检查**：
   - 仅 Admin 可以创建竞标轮次和执行分配
   - 用户只能查看自己的竞标和结果
   - 歌曲上传者才能编辑/删除自己的歌曲

2. **竞标验证**：
   - 验证代币余额，防止"信用"竞标
   - 验证竞标数量限制
   - 防止重复竞标同一歌曲

3. **CSRF 保护**：
   - 所有 POST/PUT/DELETE 请求需要 CSRF token

4. **竞标不可篡改**：
   - 竞标创建后不能修改
   - 需要删除后重新创建

---

## 13. 扩展建议

未来可以添加的功能：

1. **竞标撤销**：用户可以在轮次完成前撤销竞标
2. **最小出价增量**：防止微小的出价变化
3. **竞标历史**：记录所有竞标变更
4. **实时竞价**：WebSocket 更新竞标排名
5. **出价通知**：当有人出了更高的价格时通知
6. **竞标截止时间**：自动关闭竞标窗口
7. **保底价格**：歌曲可以设置最低竞标价格
8. **代币结算**：自动从用户账户扣款

---

## 总结

竞标系统提供了一个完整的、可扩展的、安全的竞标平台。通过清晰的 API 和灵活的数据模型，可以支持各种竞标场景。
