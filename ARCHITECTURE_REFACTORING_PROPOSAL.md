# 🏗️ XMMCG 架构重构方案

**日期**: 2026-02-10  
**作者**: GitHub Copilot  
**目标**: 实现灵活可配置的比赛流程系统

---

## 📋 目录

1. [当前架构分析](#当前架构分析)
2. [核心问题识别](#核心问题识别)
3. [新架构设计](#新架构设计)
4. [实施路线图](#实施路线图)
5. [风险评估](#风险评估)
6. [收益分析](#收益分析)

---

## 当前架构分析

### 数据模型依赖关系

```
CompetitionPhase (比赛阶段)
    ├── 通过 name 关联 → BiddingRound
    └── page_access + submissions_type
    
BiddingRound (竞标轮次)
    ├── Bid (竞标记录)
    │   ├── song (ForeignKey)
    │   └── chart (ForeignKey)
    └── BidResult (分配结果)
        ├── song (ForeignKey)
        └── chart (ForeignKey)
        
Song (歌曲)
    └── Chart (谱面)
        ├── bid_result (ForeignKey)
        ├── part_one_chart (Self ForeignKey)
        └── PeerReview (互评)
            └── PeerReviewAllocation
```

### 业务流程固化

当前系统的比赛流程是**硬编码**的：

```python
# views.py 中的判断逻辑
if phase_key__icontains='bidding':
    # 竞标逻辑
    round_obj, created = BiddingRound.objects.get_or_create(name=phase.name)
    
elif phase_key__icontains='mapping' or phase_key__icontains='chart':
    # 制谱逻辑
    submissions = Chart.objects.count()
    
elif phase_key__icontains='peer_review':
    # 互评逻辑
    submissions = Chart.objects.filter(status='submitted').count()
```

**问题**：
- ❌ 无法调整阶段顺序
- ❌ 无法跳过某个阶段
- ❌ 无法添加新类型的阶段（如投票、评委评分）
- ❌ 多轮次比赛需要重写代码

---

## 核心问题识别

### 1. 紧耦合 (Tight Coupling)

**问题表现**：
- `Chart` 必须关联 `BidResult`（不能跳过竞标直接制谱）
- `PeerReview` 只能针对 `Chart`（不能评价其他内容）
- `Bid` 的 `song`/`chart` 字段是硬编码的（无法竞标其他类型）

**代码示例**：
```python
class Chart(models.Model):
    bid_result = models.ForeignKey(
        BidResult,
        on_delete=models.CASCADE,
        null=True,  # 为了兼容性设为可空，但逻辑上要求非空
    )
```

### 2. 重复代码 (Code Duplication)

**当前实现**：
- `Bid` + `BidResult` 处理歌曲竞标
- 通过 `bid_type` 字段区分歌曲/谱面竞标
- `BiddingService.allocate_bids()` 中大量 if/else 判断

**更好的做法**：
- 抽象竞标目标为统一接口
- 使用策略模式处理不同类型

### 3. 缺乏抽象 (Lack of Abstraction)

**症状**：
- 没有"阶段"的抽象概念（只有具体的竞标、制谱、互评）
- 没有"数据流"的抽象（输入→处理→输出）
- 配置硬编码在代码中（如 `MAX_BIDS_PER_USER = 5`）

### 4. 可测试性差 (Poor Testability)

```python
# 当前：难以测试，依赖数据库和时间
def get_active_phase_for_bidding(bid_type='song', phase_id=None):
    phase = CompetitionPhase.objects.filter(
        phase_key__icontains='music_bid' if bid_type == 'song' else 'chart_bid',
        is_active=True
    ).first()
    ...
```

---

## 新架构设计

### 核心概念：Collection-Based Pipeline

#### 理念
> **比赛 = 数据流管道**  
> 每个阶段从输入Collection产生输出Collection，形成数据处理链

```
用户上传   竞标分配   用户创作   互评     排名
[空] → [歌曲] → [分配] → [谱面] → [评分] → [排行榜]
```

---

### 1️⃣ Collection（数据集合）

**定义**：一组同类型数据的抽象容器

```python
class Collection(models.Model):
    """数据集合：存放比赛中产生的任何数据实体"""
    
    COLLECTION_TYPE_CHOICES = [
        ('uploaded_songs', '上传的歌曲'),
        ('allocated_songs', '分配的歌曲'),
        ('submitted_charts_part1', '半成品谱面'),
        ('allocated_charts', '分配的谱面'),
        ('submitted_charts_final', '完整谱面'),
        ('peer_reviews', '互评评分'),
        ('judge_reviews', '评委评分'),
        ('user_votes', '用户投票'),
        # 后续可扩展...
    ]
    
    name = models.CharField(max_length=100, help_text='集合名称')
    collection_type = models.CharField(
        max_length=50, 
        choices=COLLECTION_TYPE_CHOICES,
        help_text='集合类型'
    )
    competition = models.ForeignKey(
        'Competition', 
        on_delete=models.CASCADE,
        related_name='collections'
    )
    
    # 元数据
    description = models.TextField(blank=True)
    metadata = models.JSONField(
        default=dict,
        help_text='扩展配置（如过滤条件、统计信息等）'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '数据集合'
        verbose_name_plural = '数据集合'
        ordering = ['competition', 'created_at']
    
    def __str__(self):
        return f"{self.competition.name} - {self.name}"
    
    def get_items(self):
        """获取集合中的所有条目"""
        return self.items.select_related('content_type').all()
    
    def count(self):
        """统计条目数量"""
        return self.items.count()
```

---

### 2️⃣ CollectionItem（集合条目）

**定义**：Collection中的单个数据项（多态关联）

```python
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class CollectionItem(models.Model):
    """Collection中的单个条目（支持多态）"""
    
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='所属集合'
    )
    
    # 多态关联（指向Song、Chart、BidResult、PeerReview等）
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text='关联数据类型'
    )
    object_id = models.PositiveIntegerField(help_text='关联对象ID')
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 所有者
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='数据所有者（如上传者、中标者）'
    )
    
    # 扩展元数据
    metadata = models.JSONField(
        default=dict,
        help_text='额外信息（如竞标金额、评分等）'
    )
    
    # 排序和状态
    order = models.IntegerField(default=0, help_text='排序权重')
    is_active = models.BooleanField(default=True, help_text='是否有效')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '集合条目'
        verbose_name_plural = '集合条目'
        ordering = ['collection', '-order', 'created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['collection', 'owner']),
        ]
    
    def __str__(self):
        return f"{self.collection.name} - {self.content_object}"
```

**设计说明**：
- 使用 Django 的 `GenericForeignKey` 实现多态
- 可关联任何模型：`Song`、`Chart`、`BidResult`、`PeerReview` 等
- `metadata` 字段存储额外信息（如竞标金额、评分）

---

### 3️⃣ Phase（比赛阶段）

**定义**：从输入Collection到输出Collection的转换过程

```python
class Phase(models.Model):
    """比赛阶段：数据转换器"""
    
    PHASE_TYPE_CHOICES = [
        ('user_upload', '用户上传'),      # 空 → 上传集合
        ('bidding', '竞标分配'),          # 目标集合 → 分配集合
        ('user_create', '用户创作'),      # 分配集合 → 创作集合
        ('peer_review', '互评'),          # 创作集合 → 评分集合
        ('judge_review', '评委评分'),     # 创作集合 → 评委评分集合
        ('voting', '用户投票'),           # 创作集合 → 投票集合
        ('ranking', '排名计算'),          # 评分集合 → 排名结果
        ('custom', '自定义处理'),         # 自定义逻辑
    ]
    
    competition = models.ForeignKey(
        'Competition',
        on_delete=models.CASCADE,
        related_name='phases',
        help_text='所属比赛'
    )
    
    # 基本信息
    name = models.CharField(max_length=100, help_text='阶段名称')
    description = models.TextField(blank=True, help_text='阶段描述')
    phase_type = models.CharField(
        max_length=50,
        choices=PHASE_TYPE_CHOICES,
        help_text='阶段类型（决定使用哪个Handler）'
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text='执行顺序（数字越小越靠前）'
    )
    
    # 数据流配置
    input_collection = models.ForeignKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consuming_phases',
        help_text='输入数据集（可为空，如初始上传阶段）'
    )
    output_collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='producing_phase',
        help_text='输出数据集（必需）'
    )
    
    # 时间控制
    start_time = models.DateTimeField(help_text='阶段开始时间')
    end_time = models.DateTimeField(help_text='阶段结束时间')
    
    # 权限和配置
    page_access = models.JSONField(
        default=dict,
        help_text='页面访问权限配置（如 {"songs": true, "charts": false}）'
    )
    config = models.JSONField(
        default=dict,
        help_text='''阶段特定配置，例如：
        - 竞标阶段: {"max_bids_per_user": 5, "random_allocation_cost": 200}
        - 上传阶段: {"max_uploads_per_user": 3, "allowed_formats": ["mp3"]}
        - 互评阶段: {"reviews_per_user": 8, "max_score": 50}
        '''
    )
    
    # 状态
    is_active = models.BooleanField(default=True, help_text='是否启用')
    
    # 系统字段
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '比赛阶段'
        verbose_name_plural = '比赛阶段'
        ordering = ['competition', 'order', 'start_time']
        unique_together = [('competition', 'order')]
    
    def __str__(self):
        return f"{self.competition.name} - {self.name} ({self.get_phase_type_display()})"
    
    @property
    def status(self):
        """实时计算阶段状态"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return 'disabled'
        elif now < self.start_time:
            return 'upcoming'
        elif now <= self.end_time:
            return 'active'
        else:
            return 'ended'
    
    def get_handler(self):
        """获取阶段处理器"""
        from .phase_handlers import PhaseHandlerFactory
        return PhaseHandlerFactory.get_handler(self.phase_type)
    
    def execute(self, **kwargs):
        """执行阶段逻辑（由Handler处理）"""
        handler = self.get_handler()
        handler.validate(self)
        return handler.execute(self, **kwargs)
    
    def get_user_actions(self, user):
        """获取用户可执行的操作"""
        handler = self.get_handler()
        return handler.get_user_actions(self, user)
    
    def clean(self):
        """验证配置"""
        from django.core.exceptions import ValidationError
        
        # 验证时间范围
        if self.start_time >= self.end_time:
            raise ValidationError('开始时间必须早于结束时间')
        
        # 验证输出Collection存在
        if not self.output_collection:
            raise ValidationError('必须指定输出Collection')
        
        # 部分阶段类型需要输入Collection
        if self.phase_type in ['bidding', 'user_create', 'peer_review'] and not self.input_collection:
            raise ValidationError(f'{self.get_phase_type_display()} 阶段需要输入Collection')
```

---

### 4️⃣ PhaseHandler（策略模式）

**定义**：封装每种阶段类型的具体处理逻辑

#### 基类

```python
from abc import ABC, abstractmethod
from django.core.exceptions import ValidationError

class PhaseHandler(ABC):
    """阶段处理器抽象基类"""
    
    @abstractmethod
    def validate(self, phase):
        """
        验证阶段配置是否有效
        
        Args:
            phase: Phase 对象
            
        Raises:
            ValidationError: 配置无效
        """
        pass
    
    @abstractmethod
    def execute(self, phase, **kwargs):
        """
        执行阶段的核心逻辑（通常由管理员或定时任务触发）
        
        Args:
            phase: Phase 对象
            **kwargs: 额外参数
            
        Returns:
            dict: 执行结果统计信息
        """
        pass
    
    @abstractmethod
    def get_user_actions(self, phase, user):
        """
        获取用户在该阶段可执行的操作
        
        Args:
            phase: Phase 对象
            user: User 对象
            
        Returns:
            dict: 包含可用操作、限制等信息
        """
        pass
    
    def get_statistics(self, phase):
        """
        获取阶段统计信息（可选实现）
        
        Args:
            phase: Phase 对象
            
        Returns:
            dict: 统计数据
        """
        return {
            'total_items': phase.output_collection.count() if phase.output_collection else 0,
            'participants': 0,
        }
```

#### 竞标阶段Handler

```python
class BiddingPhaseHandler(PhaseHandler):
    """竞标阶段处理器"""
    
    def validate(self, phase):
        """验证配置"""
        if not phase.input_collection:
            raise ValidationError('竞标阶段需要输入Collection（竞标目标）')
        
        config = phase.config
        if 'max_bids_per_user' not in config:
            raise ValidationError('缺少配置: max_bids_per_user')
        
        return True
    
    def execute(self, phase, **kwargs):
        """
        执行竞标分配算法
        
        算法：
        1. 获取所有竞标记录
        2. 按出价排序（同价随机）
        3. 分配目标给高出价者
        4. 未中标者随机分配剩余目标（扣除保底代币）
        5. 将分配结果写入输出Collection
        """
        from .models import Bid, BidResult
        from .bidding_service import BiddingService
        from django.contrib.auth.models import User
        
        input_items = phase.input_collection.get_items()
        config = phase.config
        
        # 获取该阶段的竞标记录
        # 注意：Bid 模型需要添加 phase 字段关联
        bids = Bid.objects.filter(phase=phase, is_dropped=False)
        
        # 调用现有的分配算法
        results = BiddingService.allocate_by_collection_items(
            items=input_items,
            bids=bids,
            max_bids_per_user=config.get('max_bids_per_user', 5),
            random_cost=config.get('random_allocation_cost', 200),
            allow_self_bidding=config.get('allow_self_bidding', False),
        )
        
        # 将分配结果写入输出Collection
        from django.contrib.contenttypes.models import ContentType
        bid_result_type = ContentType.objects.get_for_model(BidResult)
        
        for result in results:
            CollectionItem.objects.create(
                collection=phase.output_collection,
                content_type=bid_result_type,
                object_id=result.id,
                content_object=result,
                owner=result.user,
                metadata={
                    'bid_amount': result.bid_amount,
                    'allocation_type': result.allocation_type,
                }
            )
        
        return {
            'total_allocations': len(results),
            'winners': len([r for r in results if r.allocation_type == 'win']),
            'random_allocations': len([r for r in results if r.allocation_type == 'random']),
        }
    
    def get_user_actions(self, phase, user):
        """获取用户竞标操作"""
        from .models import Bid
        
        input_items = phase.input_collection.get_items()
        max_bids = phase.config.get('max_bids_per_user', 5)
        
        user_bids = Bid.objects.filter(
            phase=phase,
            user=user,
            is_dropped=False
        )
        
        return {
            'action_type': 'submit_bid',
            'available_items': [
                {
                    'id': item.object_id,
                    'type': item.content_type.model,
                    'object': item.content_object,
                } for item in input_items
            ],
            'user_bids': list(user_bids.values('id', 'target_id', 'amount')),
            'user_bids_count': user_bids.count(),
            'max_bids': max_bids,
            'can_bid': user_bids.count() < max_bids,
        }
```

#### 用户上传Handler

```python
class UserUploadPhaseHandler(PhaseHandler):
    """用户上传阶段处理器"""
    
    def validate(self, phase):
        """验证配置"""
        config = phase.config
        
        if 'upload_type' not in config:
            raise ValidationError('缺少配置: upload_type（如 "song", "image"）')
        
        if 'max_uploads_per_user' not in config:
            raise ValidationError('缺少配置: max_uploads_per_user')
        
        return True
    
    def execute(self, phase, **kwargs):
        """
        上传阶段无需系统执行，用户自行上传
        此方法仅用于统计
        """
        return {
            'total_uploads': phase.output_collection.count(),
            'participants': phase.output_collection.items.values('owner').distinct().count(),
        }
    
    def get_user_actions(self, phase, user):
        """获取用户上传操作"""
        config = phase.config
        max_uploads = config.get('max_uploads_per_user', 3)
        
        user_uploads = CollectionItem.objects.filter(
            collection=phase.output_collection,
            owner=user
        )
        
        return {
            'action_type': 'upload',
            'upload_type': config.get('upload_type', 'song'),
            'uploaded_count': user_uploads.count(),
            'max_uploads': max_uploads,
            'can_upload': user_uploads.count() < max_uploads,
            'allowed_formats': config.get('allowed_formats', []),
            'max_file_size_mb': config.get('max_file_size_mb', 10),
        }
```

#### 用户创作Handler

```python
class UserCreatePhaseHandler(PhaseHandler):
    """用户创作阶段处理器（如制谱）"""
    
    def validate(self, phase):
        if not phase.input_collection:
            raise ValidationError('创作阶段需要输入Collection（创作依据）')
        
        config = phase.config
        if 'creation_type' not in config:
            raise ValidationError('缺少配置: creation_type（如 "chart"）')
        
        return True
    
    def execute(self, phase, **kwargs):
        """创作阶段无需系统执行"""
        return {
            'total_creations': phase.output_collection.count(),
            'participants': phase.output_collection.items.values('owner').distinct().count(),
        }
    
    def get_user_actions(self, phase, user):
        """获取用户创作操作"""
        from .models import Chart
        from django.contrib.contenttypes.models import ContentType
        
        config = phase.config
        creation_type = config.get('creation_type', 'chart')
        
        # 获取用户在输入Collection中的分配
        user_input_items = CollectionItem.objects.filter(
            collection=phase.input_collection,
            owner=user
        )
        
        # 检查用户是否已提交
        user_output_items = CollectionItem.objects.filter(
            collection=phase.output_collection,
            owner=user
        )
        
        return {
            'action_type': 'create',
            'creation_type': creation_type,
            'assigned_items': [
                {
                    'id': item.object_id,
                    'type': item.content_type.model,
                    'object': item.content_object,
                } for item in user_input_items
            ],
            'submitted_items': list(user_output_items.values()),
            'can_create': user_input_items.exists() and not user_output_items.exists(),
            'is_partial': config.get('is_partial', False),
            'required_files': config.get('required_files', []),
        }
```

#### 互评Handler

```python
class PeerReviewPhaseHandler(PhaseHandler):
    """互评阶段处理器"""
    
    def validate(self, phase):
        if not phase.input_collection:
            raise ValidationError('互评阶段需要输入Collection（评分目标）')
        
        config = phase.config
        if 'reviews_per_user' not in config:
            raise ValidationError('缺少配置: reviews_per_user')
        if 'max_score' not in config:
            raise ValidationError('缺少配置: max_score')
        
        return True
    
    def execute(self, phase, **kwargs):
        """
        执行互评任务分配
        
        算法：
        1. 获取所有待评项目（输入Collection）
        2. 获取所有评分者（参赛用户）
        3. 平衡分配：每个用户评分N个，每个项目被评分N次
        4. 创建 PeerReviewAllocation 记录
        """
        from .models import PeerReviewAllocation
        from django.contrib.auth.models import User
        import random
        
        config = phase.config
        reviews_per_user = config.get('reviews_per_user', 8)
        allocation_algorithm = config.get('allocation_algorithm', 'balanced')
        
        # 获取待评项目
        items_to_review = list(phase.input_collection.get_items())
        
        # 获取评分者（所有参赛用户）
        reviewers = User.objects.filter(
            # 假设参赛用户是提交过创作的用户
            id__in=CollectionItem.objects.filter(
                collection__competition=phase.competition
            ).values_list('owner_id', flat=True).distinct()
        )
        
        allocations = []
        
        if allocation_algorithm == 'balanced':
            # 平衡分配算法
            # ...（复用现有的分配逻辑）
            pass
        
        # 批量创建分配记录
        PeerReviewAllocation.objects.bulk_create(allocations)
        
        return {
            'total_allocations': len(allocations),
            'reviewers_count': reviewers.count(),
            'items_count': len(items_to_review),
        }
    
    def get_user_actions(self, phase, user):
        """获取用户互评操作"""
        from .models import PeerReviewAllocation, PeerReview
        
        # 获取分配给用户的任务
        allocations = PeerReviewAllocation.objects.filter(
            # phase=phase,  # 需要添加 phase 字段
            reviewer=user
        )
        
        completed_reviews = PeerReview.objects.filter(
            allocation__in=allocations
        )
        
        return {
            'action_type': 'peer_review',
            'total_tasks': allocations.count(),
            'completed_tasks': completed_reviews.count(),
            'pending_tasks': allocations.filter(status='pending'),
            'max_score': phase.config.get('max_score', 50),
        }
```

#### Handler工厂

```python
class PhaseHandlerFactory:
    """阶段处理器工厂"""
    
    _handlers = {
        'user_upload': UserUploadPhaseHandler(),
        'bidding': BiddingPhaseHandler(),
        'user_create': UserCreatePhaseHandler(),
        'peer_review': PeerReviewPhaseHandler(),
        # 可扩展...
    }
    
    @classmethod
    def get_handler(cls, phase_type):
        """根据阶段类型获取Handler"""
        handler = cls._handlers.get(phase_type)
        if not handler:
            raise ValueError(f'未知的阶段类型: {phase_type}')
        return handler
    
    @classmethod
    def register_handler(cls, phase_type, handler):
        """注册新的Handler（支持扩展）"""
        if not isinstance(handler, PhaseHandler):
            raise TypeError('Handler 必须继承 PhaseHandler 基类')
        cls._handlers[phase_type] = handler
```

---

### 5️⃣ Competition（比赛）

**定义**：一系列Phase的有序组合（Pipeline）

```python
class Competition(models.Model):
    """比赛：完整的数据流管道"""
    
    name = models.CharField(max_length=200, help_text='比赛名称')
    description = models.TextField(blank=True, help_text='比赛描述')
    
    # 时间范围
    start_date = models.DateTimeField(help_text='比赛开始日期')
    end_date = models.DateTimeField(help_text='比赛结束日期')
    
    # 状态
    is_active = models.BooleanField(default=True, help_text='是否启用')
    is_published = models.BooleanField(default=False, help_text='是否公开')
    
    # 系统字段
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '比赛'
        verbose_name_plural = '比赛'
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name
    
    def get_phases(self):
        """获取所有启用的阶段（按order排序）"""
        return self.phases.filter(is_active=True).order_by('order')
    
    def get_current_phase(self):
        """获取当前活跃的阶段"""
        from django.utils import timezone
        now = timezone.now()
        
        return self.phases.filter(
            is_active=True,
            start_time__lte=now,
            end_time__gte=now
        ).first()
    
    def validate_pipeline(self):
        """
        验证Pipeline的完整性
        
        检查：
        1. 阶段时间不重叠
        2. 输入/输出Collection链接正确
        3. 配置有效性
        """
        from django.core.exceptions import ValidationError
        import warnings
        
        phases = list(self.get_phases())
        
        for i, phase in enumerate(phases):
            # 检查时间顺序
            if i > 0:
                prev_phase = phases[i - 1]
                if phase.start_time < prev_phase.end_time:
                    raise ValidationError(
                        f'阶段 "{phase.name}" 的开始时间早于前一阶段 "{prev_phase.name}" 的结束时间'
                    )
            
            # 检查Collection链接
            if phase.input_collection:
                # 输入Collection应该是前面某个Phase的输出
                is_valid_input = any(
                    p.output_collection == phase.input_collection
                    for p in phases[:i]
                )
                
                if not is_valid_input:
                    warnings.warn(
                        f'阶段 "{phase.name}" 的输入Collection不是前序阶段的输出'
                    )
            
            # 验证Handler配置
            try:
                handler = phase.get_handler()
                handler.validate(phase)
            except Exception as e:
                raise ValidationError(
                    f'阶段 "{phase.name}" 配置无效: {str(e)}'
                )
        
        return True
    
    def get_pipeline_graph(self):
        """
        生成Pipeline的可视化图（用于管理界面）
        
        Returns:
            dict: 图数据（可用于前端渲染）
        """
        phases = list(self.get_phases())
        
        nodes = []
        edges = []
        
        for phase in phases:
            nodes.append({
                'id': f'phase_{phase.id}',
                'label': phase.name,
                'type': phase.phase_type,
                'status': phase.status,
            })
            
            if phase.input_collection:
                nodes.append({
                    'id': f'collection_{phase.input_collection.id}',
                    'label': phase.input_collection.name,
                    'type': 'collection',
                })
                edges.append({
                    'from': f'collection_{phase.input_collection.id}',
                    'to': f'phase_{phase.id}',
                })
            
            nodes.append({
                'id': f'collection_{phase.output_collection.id}',
                'label': phase.output_collection.name,
                'type': 'collection',
            })
            edges.append({
                'from': f'phase_{phase.id}',
                'to': f'collection_{phase.output_collection.id}',
            })
        
        return {'nodes': nodes, 'edges': edges}
```

---

## 实施路线图

### 阶段1：准备工作（1-2周）

#### 1.1 数据库设计
- [ ] 创建 `Competition` 模型
- [ ] 创建 `Collection` 模型
- [ ] 创建 `CollectionItem` 模型
- [ ] 创建 `Phase` 模型
- [ ] 添加必要的索引和约束

#### 1.2 现有模型适配
- [ ] `Bid` 添加 `phase` 字段（ForeignKey to Phase）
- [ ] `BidResult` 添加 `phase` 字段
- [ ] `Chart` 保持兼容性（暂时保留 `bid_result` 字段）
- [ ] `PeerReviewAllocation` 添加 `phase` 字段

#### 1.3 迁移脚本
```python
# migrations/0XXX_add_pipeline_models.py
from django.db import migrations

def migrate_existing_data(apps, schema_editor):
    """将现有数据迁移到新架构"""
    CompetitionPhase = apps.get_model('songs', 'CompetitionPhase')
    Competition = apps.get_model('songs', 'Competition')
    Phase = apps.get_model('songs', 'Phase')
    Collection = apps.get_model('songs', 'Collection')
    
    # 创建默认比赛
    competition = Competition.objects.create(
        name='2026年春季比赛',
        start_date='2026-02-01',
        end_date='2026-04-30',
    )
    
    # 迁移现有的 CompetitionPhase 为新的 Phase
    for old_phase in CompetitionPhase.objects.all():
        # 创建输出Collection
        output_collection = Collection.objects.create(
            name=f'{old_phase.name} - 输出',
            collection_type=_infer_collection_type(old_phase.phase_key),
            competition=competition,
        )
        
        # 创建Phase
        Phase.objects.create(
            competition=competition,
            name=old_phase.name,
            phase_type=_infer_phase_type(old_phase.phase_key),
            order=old_phase.order,
            output_collection=output_collection,
            start_time=old_phase.start_time,
            end_time=old_phase.end_time,
            page_access=old_phase.page_access,
        )

class Migration(migrations.Migration):
    dependencies = [...]
    
    operations = [
        # 创建模型
        migrations.CreateModel(name='Competition', ...),
        migrations.CreateModel(name='Collection', ...),
        migrations.CreateModel(name='CollectionItem', ...),
        migrations.CreateModel(name='Phase', ...),
        
        # 数据迁移
        migrations.RunPython(migrate_existing_data),
    ]
```

---

### 阶段2：核心实现（2-3周）

#### 2.1 Handler实现
- [ ] 实现 `PhaseHandler` 抽象基类
- [ ] 实现 `BiddingPhaseHandler`
- [ ] 实现 `UserUploadPhaseHandler`
- [ ] 实现 `UserCreatePhaseHandler`
- [ ] 实现 `PeerReviewPhaseHandler`
- [ ] 实现 `PhaseHandlerFactory`

#### 2.2 Service层适配
- [ ] 重构 `BiddingService` 支持 `CollectionItem`
- [ ] 创建 `CollectionService` 管理集合操作
- [ ] 创建 `PhaseService` 管理阶段执行

#### 2.3 API更新
```python
# views.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_competition_info(request, competition_id):
    """获取比赛信息和Pipeline"""
    competition = get_object_or_404(Competition, id=competition_id)
    
    return Response({
        'competition': CompetitionSerializer(competition).data,
        'phases': PhaseSerializer(competition.get_phases(), many=True).data,
        'current_phase': PhaseSerializer(competition.get_current_phase()).data,
        'pipeline_graph': competition.get_pipeline_graph(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_phase_actions(request, phase_id):
    """获取用户在某阶段的可用操作"""
    phase = get_object_or_404(Phase, id=phase_id)
    actions = phase.get_user_actions(request.user)
    
    return Response(actions)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def execute_phase(request, phase_id):
    """执行阶段逻辑（如分配竞标结果）"""
    phase = get_object_or_404(Phase, id=phase_id)
    
    if phase.status != 'ended':
        return Response(
            {'error': '只能对已结束的阶段执行分配'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    results = phase.execute()
    
    return Response({
        'success': True,
        'results': results,
    })
```

---

### 阶段3：前端适配（1-2周）

#### 3.1 API集成
```javascript
// api/competition.js

export const getCompetitionInfo = async (competitionId) => {
  return await api.get(`/competitions/${competitionId}/`)
}

export const getUserPhaseActions = async (phaseId) => {
  return await api.get(`/phases/${phaseId}/actions/`)
}

export const executePhase = async (phaseId) => {
  return await api.post(`/phases/${phaseId}/execute/`)
}
```

#### 3.2 组件更新
- [ ] 更新 `PhaseTimeline.vue` 显示新的Pipeline
- [ ] 更新 `Home.vue` 使用新的API
- [ ] 创建 `PipelineVisualizer.vue` 可视化Pipeline

#### 3.3 路由守卫更新
```javascript
// router/index.js

router.beforeEach(async (to, from, next) => {
  if (to.meta.requiresAuth) {
    const competition = await getCompetitionInfo(currentCompetitionId)
    const currentPhase = competition.current_phase
    
    // 基于当前Phase的 page_access 控制路由
    const pageAccess = currentPhase.page_access
    
    if (to.name === 'Songs' && !pageAccess.songs) {
      next({ name: 'Home' })
    } else if (to.name === 'Charts' && !pageAccess.charts) {
      next({ name: 'Home' })
    } else {
      next()
    }
  } else {
    next()
  }
})
```

---

### 阶段4：测试与优化（1周）

#### 4.1 单元测试
```python
# tests/test_phase_handlers.py

class BiddingPhaseHandlerTestCase(TestCase):
    def test_execute_bidding(self):
        # 创建测试数据
        competition = Competition.objects.create(...)
        input_collection = Collection.objects.create(...)
        output_collection = Collection.objects.create(...)
        
        phase = Phase.objects.create(
            competition=competition,
            phase_type='bidding',
            input_collection=input_collection,
            output_collection=output_collection,
            config={'max_bids_per_user': 5},
        )
        
        # 执行
        results = phase.execute()
        
        # 验证
        self.assertEqual(output_collection.count(), expected_count)
```

#### 4.2 集成测试
- [ ] 测试完整的比赛流程
- [ ] 测试异常情况处理
- [ ] 性能测试（大数据量）

#### 4.3 文档更新
- [ ] 更新API文档
- [ ] 更新管理员手册
- [ ] 创建Pipeline配置指南

---

### 阶段5：渐进式迁移（2-3周）

#### 5.1 双轨运行
- 保留旧的 `CompetitionPhase` 系统
- 新系统与旧系统并行（通过配置切换）
- 逐步迁移现有数据

#### 5.2 A/B测试
- 小范围启用新系统
- 收集反馈和问题
- 调整优化

#### 5.3 完全切换
- 确认新系统稳定
- 停用旧系统
- 清理废弃代码

---

## 风险评估

### 高风险

#### 1. 数据迁移风险
**风险**：现有数据迁移失败导致数据丢失

**缓解措施**：
- 完整备份数据库
- 在测试环境充分测试迁移脚本
- 提供回滚方案
- 双轨运行期间保留旧数据

#### 2. 性能风险
**风险**：GenericForeignKey 查询性能差

**缓解措施**：
- 使用 `select_related()` 和 `prefetch_related()`
- 添加数据库索引
- 缓存频繁查询的数据
- 考虑使用专用中间表替代GenericForeignKey

### 中风险

#### 3. 兼容性风险
**风险**：前端组件大量依赖旧API

**缓解措施**：
- 提供兼容层（旧API转发到新系统）
- 分阶段更新前端组件
- 保留向后兼容性

#### 4. 学习曲线
**风险**：新架构复杂，团队学习成本高

**缓解措施**：
- 编写详细文档
- 提供代码示例
- 团队培训

### 低风险

#### 5. 扩展性风险
**风险**：未来需求变化导致架构不适用

**缓解措施**：
- 使用抽象接口和策略模式
- Handler可插拔设计
- 预留扩展点

---

## 收益分析

### 短期收益（3个月内）

#### 1. 提高开发效率
- **添加新阶段类型**：从2-3天 → 2-3小时
- **修改比赛流程**：从修改代码 → 配置数据

#### 2. 减少Bug
- 解耦后各模块独立测试
- 减少修改一处影响全局的风险

#### 3. 提升可维护性
- 代码逻辑清晰
- 易于定位问题

### 中期收益（6个月-1年）

#### 4. 支持多样化比赛
- 单轮快速赛
- 多轮循环赛
- 混合模式比赛

#### 5. 降低运营成本
- 管理员可通过Admin配置比赛流程
- 无需开发人员介入

#### 6. 提升用户体验
- 流程可视化
- 清晰的阶段指引

### 长期收益（1年以上）

#### 7. 平台化能力
- 支持不同类型的创作比赛（不限于音游谱面）
- 可作为通用比赛平台

#### 8. 商业价值
- 支持定制化服务
- 快速响应客户需求

---

## 总结

### 核心理念
> **比赛 = 数据流管道**  
> 通过 Collection 和 Phase 的组合，实现灵活可配置的比赛流程

### 关键优势

1. **解耦**：Phase 不依赖具体数据类型
2. **灵活**：通过配置定义流程，无需修改代码
3. **可扩展**：Handler 策略模式，轻松添加新类型
4. **可复用**：现有业务逻辑（BiddingService等）无缝集成
5. **向后兼容**：渐进式迁移，风险可控

### 下一步行动

1. **评审架构设计**：团队讨论，征求意见
2. **原型开发**：实现核心模型和1-2个Handler
3. **小范围测试**：在测试环境验证可行性
4. **制定详细计划**：确定时间表和资源分配
5. **正式开发**：按路线图分阶段实施

---

**附录**：
- [详细数据库Schema设计](./SCHEMA_DESIGN.md)（待补充）
- [Handler开发指南](./HANDLER_GUIDE.md)（待补充）
- [Pipeline配置示例](./PIPELINE_EXAMPLES.md)（待补充）

---

**文档版本**: v1.0  
**最后更新**: 2026-02-10
