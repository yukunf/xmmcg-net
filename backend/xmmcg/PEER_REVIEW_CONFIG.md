# 互评系统配置说明

## 配置方式

互评系统的关键参数可以通过以下方式配置（按优先级从高到低）：

1. **环境变量文件** (推荐)
2. **Django settings.py** 
3. **代码默认值**

## 可配置参数

### 1. PEER_REVIEW_TASKS_PER_USER
- **说明**: 每个用户需要完成的评分任务数
- **默认值**: 8
- **使用场景**: 
  - 12人场景：每人评8张 → 每谱面被评8次（12张谱面）
  - 8人场景：每人评6张 → 每谱面被评6次（8张谱面）
- **配置方法**:
  ```bash
  # 在 login_credentials.env 或 .env 文件中添加
  PEER_REVIEW_TASKS_PER_USER=8
  ```

### 2. PEER_REVIEW_MAX_SCORE
- **说明**: 互评满分
- **默认值**: 50
- **配置方法**:
  ```bash
  # 在 login_credentials.env 或 .env 文件中添加
  PEER_REVIEW_MAX_SCORE=50
  ```

## 环境变量文件配置示例

在项目根目录的 `login_credentials.env` 文件中添加：

```bash
# 互评系统配置
PEER_REVIEW_TASKS_PER_USER=8
PEER_REVIEW_MAX_SCORE=50
```

## 动态计算说明

系统会自动根据参与人数和谱面数量进行平衡计算：

**平衡公式**: 
```
评分者数 × 每人任务数 = 谱面数 × 每谱面评分数
```

**示例**:
- 12个评分者 × 8个任务 = 12张谱面 × 8次评分 = 96次总评分 ✓
- 8个评分者 × 6个任务 = 8张谱面 × 6次评分 = 48次总评分 ✓

## 注意事项

1. **两部分合作谱面**: 每张谱面有2个贡献者（第一部分作者 + 第二部分续写者），他们都不能评这张谱面
2. **数学约束**: 系统会自动验证配置是否能够平衡分配，如果不能平衡会提示错误
3. **修改生效**: 修改环境变量后需要重启Django服务器

## API调用

在调用互评分配API时，可以动态覆盖默认值：

```python
# 使用默认配置（从settings读取）
POST /api/peer-reviews/allocate/{round_id}/

# 或指定自定义值
POST /api/peer-reviews/allocate/{round_id}/
{
    "reviews_per_user": 6
}
```
