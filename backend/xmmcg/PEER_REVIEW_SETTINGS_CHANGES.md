# 互评系统配置修改说明

## ✅ 已完成的修改

已成功将互评系统的评分任务数量提取到 Django settings，方便动态调整。

## 📝 修改的文件

### 1. `xmmcg/settings.py`
添加了互评系统配置段：
```python
# ========= Peer Review System Settings =========
PEER_REVIEW_TASKS_PER_USER = config('PEER_REVIEW_TASKS_PER_USER', default=8, cast=int)
PEER_REVIEW_MAX_SCORE = config('PEER_REVIEW_MAX_SCORE', default=50, cast=int)
```

### 2. `songs/bidding_service.py`
- 导入了 `django.conf.settings`
- `allocate_peer_reviews()` 方法改为从 settings 读取默认值
- `submit_peer_review()` 方法中的硬编码数字8改为从 settings 读取

### 3. `songs/models.py`
更新了常量注释，说明优先使用 settings.py 配置

### 4. `PEER_REVIEW_CONFIG.md`（新建）
完整的配置说明文档

## 🎯 如何调整配置

### 方法1: 环境变量（推荐）
在项目根目录的 `login_credentials.env` 文件中添加：
```bash
# 互评系统配置
PEER_REVIEW_TASKS_PER_USER=10  # 改为每人评10张
PEER_REVIEW_MAX_SCORE=100      # 改为满分100
```

### 方法2: 直接修改 settings.py
```python
PEER_REVIEW_TASKS_PER_USER = 10
PEER_REVIEW_MAX_SCORE = 100
```

### 方法3: API调用时动态指定
```python
POST /api/peer-reviews/allocate/{round_id}/
{
    "reviews_per_user": 10  # 临时覆盖配置
}
```

## ⚙️ 配置示例

### 12人比赛（每人2张谱面）
```bash
PEER_REVIEW_TASKS_PER_USER=8
```
- 12个评分者 × 8个任务 = 96次评分
- 12张谱面 × 8次被评 = 96次评分 ✓

### 16人比赛（每人2张谱面）
```bash
PEER_REVIEW_TASKS_PER_USER=6
```
- 16个评分者 × 6个任务 = 96次评分
- 16张谱面 × 6次被评 = 96次评分 ✓

## 🔄 修改后的操作

1. 修改环境变量或 settings.py
2. 重启 Django 服务器
3. 测试新配置是否生效

## ✨ 优势

- ✅ 无需修改代码即可调整评分任务数
- ✅ 支持环境变量配置，便于不同环境使用不同配置
- ✅ 向后兼容，保留了默认值
- ✅ API支持动态覆盖配置
