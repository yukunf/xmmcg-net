# 🏗️ XMMCG 架构改进方案 V2.5（混合架构）

**日期**: 2026-02-10  
**作者**: GitHub Copilot  
**目标**: 轻量级重构，实现灵活的比赛流程配置

---

## 📑 文档导读

| 章节 | 内容 | 适合读者 |
|------|------|---------|
| [核心原则](#-核心原则) | 设计指导思想 | 所有人 |
| [当前问题](#当前问题回顾) | 现有架构痛点分析 | 开发者 |
| [改进方案](#改进方案混合架构v25) | V2.5混合架构设计 | 架构师、开发者 |
| [实际使用](#-collection--phase-完整示例解决用户提出的两个问题) | 完整使用示例 | 开发者、管理员 |
| [前端适配](#前端适配完全动态化后台配置驱动) | 前端动态配置方案 | 前端开发者 |
| [实施路线图](#-实施路线图v25混合架构) | 详细实施步骤 | 项目经理、开发者 |
| [优势总结](#-优势总结v25混合架构) | 方案对比与优势 | 决策者 |

---

## 🎯 TL;DR（3分钟速览）

### 问题
现有架构使用硬编码的`phase_key`判断阶段类型，无法灵活调整比赛流程。

### 解决方案
**V2.5混合架构** = 轻量级Collection（数据流） + 固定action_type（类型安全）

### 核心改动
- ✅ 新增1个`Collection`模型（存储查询条件，不存储实际数据）
- ✅ `CompetitionPhase`新增7个字段
- ✅ 新增2个API端点（配置拉取）
- ✅ 原有数据模型（Song/Chart）完全不变

### 关键特性
1. **后台配置前端拉取**：`max_uploads`等限制从后台动态获取
2. **Collection-based权限**：`require_in_input_collection`自动检查用户资格
3. **零数据迁移成本**：Collection不存储数据，只存查询条件
4. **无N+1查询问题**：直接查询目标表，无GenericForeignKey

### 实施时间
**2-3周**（准备1天 + 开发2周 + 测试部署3天）

---

## 📋 核心原则

1. **最小化改动** - 保留现有数据模型（Song/Chart/Bid 等）
2. **基于现实** - 只支持三种页面：songs/charts/eval
3. **渐进增强** - 在现有 CompetitionPhase 基础上改进
4. **向后兼容** - 前端无需大改

---

## 当前问题回顾

### 现有架构的痛点

```python
# 问题1：硬编码的阶段类型判断
if phase_key__icontains='bidding':
    # 竞标逻辑
elif phase_key__icontains='mapping':
    # 制谱逻辑
elif phase_key__icontains='peer_review':
    # 互评逻辑
```

**问题**：
- ❌ 无法灵活调整阶段顺序
- ❌ 无法跳过某些阶段
- ❌ 添加新流程需要改代码

### 用户的核心需求

> 实际比赛不会脱离 **歌曲/谱面/评价** 三种操作，但需要能够：
> 1. **重排比赛结构**（如跳过竞标、多轮制谱）
> 2. **区分两种阶段**：用户操作 vs 系统执行

---

## 改进方案：混合架构（V2.5）

### 核心思路

> **引入轻量级 Collection + 固定的 action_type，兼顾类型安全和数据流清晰**

### 架构图解

```
Phase (固定的10种action_type)
  ├── input_collection (可选) ──→ Collection (轻量级)
  │                                  └── 查询条件（JSON）
  └── output_collection (必需) ──→ Collection
                                     └── 查询条件（JSON）
```

---

### 1️⃣ 轻量级 Collection 模型

```python
class Collection(models.Model):
    """数据集合（轻量级，不存储实际数据，只存储查询条件）"""
    
    COLLECTION_TYPE_CHOICES = [
        ('uploaded_songs', '上传的歌曲'),
        ('allocated_songs', '分配的歌曲（BidResult）'),
        ('submitted_charts', '提交的谱面'),
        ('allocated_charts', '分配的谱面（BidResult）'),
        ('peer_reviews', '互评评分'),
    ]
    
    name = models.CharField(max_length=100, help_text='集合名称')
    collection_type = models.CharField(
        max_length=30,
        choices=COLLECTION_TYPE_CHOICES,
        help_text='集合类型（决定查询哪个模型）'
    )
    
    # 查询条件（存储为 JSON）
    query_filter = models.JSONField(
        default=dict,
        help_text='查询过滤条件，如 {"status": "submitted", "created_at__gte": "2026-02-01"}'
    )
    
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '数据集合'
        verbose_name_plural = '数据集合'
    
    def __str__(self):
        return f"{self.name} ({self.get_collection_type_display()})"
    
    def get_queryset(self):
        """根据 collection_type 和 query_filter 返回 QuerySet"""
        if self.collection_type == 'uploaded_songs':
            from .models import Song
            qs = Song.objects.all()
        
        elif self.collection_type == 'allocated_songs':
            from .models import BidResult
            qs = BidResult.objects.filter(bid_type='song')
        
        elif self.collection_type == 'submitted_charts':
            from .models import Chart
            qs = Chart.objects.all()
        
        elif self.collection_type == 'allocated_charts':
            from .models import BidResult
            qs = BidResult.objects.filter(bid_type='chart')
        
        elif self.collection_type == 'peer_reviews':
            from .models import PeerReview
            qs = PeerReview.objects.all()
        
        else:
            return None
        
        # 应用查询过滤条件
        if self.query_filter:
            qs = qs.filter(**self.query_filter)
        
        return qs
    
    def count(self):
        """统计数量"""
        qs = self.get_queryset()
        return qs.count() if qs else 0
    
    def contains_user(self, user):
        """检查用户是否在此Collection中（用于参与限制）"""
        qs = self.get_queryset()
        if not qs:
            return False
        
        # 根据collection_type判断用户关联字段
        if self.collection_type in ['uploaded_songs']:
            return qs.filter(user=user).exists()
        
        elif self.collection_type in ['allocated_songs', 'allocated_charts']:
            return qs.filter(user=user).exists()
        
        elif self.collection_type == 'submitted_charts':
            return qs.filter(user=user).exists()
        
        elif self.collection_type == 'peer_reviews':
            # 检查是否有该用户的评分分配
            return qs.filter(reviewer=user).exists()
        
        return False
```

---

### 2️⃣ 改进 Phase 模型（混合版）

```python
class Phase(models.Model):
    """比赛阶段（改进版）"""
    
    # ========== 新增字段 ==========
    
    # 阶段分类（对应前端三个页面）
    PHASE_CATEGORY_CHOICES = [
        ('song', '歌曲相关'),     # 对应 /songs 页面
        ('chart', '谱面相关'),    # 对应 /charts 页面
        ('review', '评价相关'),   # 对应 /eval 页面
    ]
    phase_category = models.CharField(
        max_length=20,
        choices=PHASE_CATEGORY_CHOICES,
        default='song',
        help_text='阶段类别（决定前端页面访问）',
        db_index=True
    )
    
    # 执行类型（核心区分）
    EXECUTION_TYPE_CHOICES = [
        ('user_action', '用户操作'),       # 等待用户上传/创作/评分
        ('system_execute', '系统执行'),    # 自动执行（如竞标分配、互评分配）
    ]
    execution_type = models.CharField(
        max_length=20,
        choices=EXECUTION_TYPE_CHOICES,
        default='user_action',
        help_text='执行类型：用户操作 or 系统自动执行'
    )
    
    # 阶段动作（具体操作）
    ACTION_TYPE_CHOICES = [
        # 歌曲相关
        ('upload_song', '上传歌曲'),
        ('bid_song', '竞标歌曲'),
        ('allocate_song', '分配歌曲'),      # 系统执行
        
        # 谱面相关
        ('create_chart', '制作谱面'),
        ('bid_chart', '竞标谱面'),
        ('allocate_chart', '分配谱面'),     # 系统执行
        
        # 评价相关
        ('peer_review', '互评'),
        ('allocate_review', '分配评分任务'), # 系统执行
        ('judge_review', '评委评分'),
        ('voting', '用户投票'),
    ]
    action_type = models.CharField(
        max_length=30,
        choices=ACTION_TYPE_CHOICES,
        help_text='具体动作类型'
    )
    
    # ========== Collection关联（V2.5核心）==========
    
    input_collection = models.ForeignKey(
        'Collection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consuming_phases',
        help_text='输入数据集合（可选，用于限制参与者和提供数据源）'
    )
    
    output_collection = models.ForeignKey(
        'Collection',
        on_delete=models.CASCADE,
        related_name='producing_phase',
        help_text='输出数据集合（该阶段产生的数据将存入此集合）'
    )
    
    # 参与限制（解决用户提出的问题2）
    require_in_input_collection = models.BooleanField(
        default=False,
        help_text='是否要求用户必须存在于input_collection中才能参与此阶段'
    )
    
    # 依赖关系（用于定义流程顺序）
    depends_on = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dependent_phases',
        help_text='依赖的前置阶段（时间顺序）'
    )
    
    # ========== 保留原有字段 ==========
    
    name = models.CharField(max_length=100, help_text='阶段名称')
    description = models.TextField(blank=True, help_text='阶段描述')
    
    start_time = models.DateTimeField(help_text='开始时间')
    end_time = models.DateTimeField(help_text='结束时间')
    
    order = models.PositiveIntegerField(default=0, help_text='显示顺序')
    is_active = models.BooleanField(default=True, help_text='是否启用')
    
    # 页面访问权限（保留，但可根据 phase_category 自动生成）
    page_access = models.JSONField(
        default=dict,
        help_text='页面访问权限'
    )
    
    # 配置（灵活扩展）
    config = models.JSONField(
        default=dict,
        help_text='''阶段配置，例如：
        - 上传歌曲: {"max_uploads": 3, "allowed_formats": ["mp3"]}
        - 竞标: {"max_bids": 5, "random_cost": 200}
        - 制谱: {"is_partial": true, "required_files": ["maidata.txt"]}
        - 互评: {"reviews_per_user": 8, "max_score": 50}
        '''
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '比赛阶段'
        verbose_name_plural = '比赛阶段'
        ordering = ['order', 'start_time']
    
    def __str__(self):
        return f"{self.name} [{self.get_action_type_display()}]"
    
    @property
    def status(self):
        """实时计算状态"""
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
    
    def save(self, *args, **kwargs):
        """自动设置 page_access"""
        if not self.page_access:
            self.page_access = self.get_default_page_access()
        super().save(*args, **kwargs)
    
    def get_default_page_access(self):
        """根据 phase_category 自动生成 page_access"""
        base_access = {
            'songs': False,
            'charts': False,
            'eval': False,
            'profile': True,
        }
        
        # 根据阶段类别开放对应页面
        if self.phase_category == 'song':
            base_access['songs'] = True
        elif self.phase_category == 'chart':
            base_access['charts'] = True
        elif self.phase_category == 'review':
            base_access['eval'] = True
        
        return base_access
    
    def can_user_participate(self, user):
        """
        检查用户是否可以参与此阶段（解决用户问题2：参与限制）
        
        Returns:
            (bool, str): (是否允许, 错误信息)
        """
        # 检查阶段是否处于活跃状态
        if self.status != 'active':
            return False, f'阶段未开放（当前状态：{self.status}）'
        
        # 检查是否需要在input_collection中
        if self.require_in_input_collection and self.input_collection:
            if not self.input_collection.contains_user(user):
                return False, f'您不在参与者名单中（需要在"{self.input_collection.name}"集合中）'
        
        return True, ''
    
    def get_user_action_config(self, user):
        """
        获取用户可用的操作配置（解决用户问题1：后台配置前端拉取）
        
        Returns:
            dict: 包含所有前端需要的配置信息，前端可直接使用
        """
        can_participate, error_msg = self.can_user_participate(user)
        
        base_config = {
            # 基本信息
            'phase_id': self.id,
            'phase_name': self.name,
            'phase_category': self.phase_category,
            'action_type': self.action_type,
            'execution_type': self.execution_type,
            
            # 权限
            'can_participate': can_participate,
            'error_message': error_msg,
            
            # 时间
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            
            # 页面访问
            'page_access': self.page_access,
        }
        
        # 合并后台配置的config字段（包含max_uploads, max_bids等）
        base_config.update(self.config)
        
        return base_config
    
    def get_source_data(self):
        """
        获取该阶段的数据来源
        
        Returns:
            QuerySet: 根据 depends_on 和 action_type 返回相应数据
        """
        if not self.depends_on:
            return None
        
        prev_phase = self.depends_on
        
        # 根据前一阶段的 action_type 确定数据来源
        if prev_phase.action_type == 'upload_song':
            from .models import Song
            return Song.objects.all()
        
        elif prev_phase.action_type == 'allocate_song':
            from .models import BidResult
            return BidResult.objects.filter(
                bidding_round__competition_phase=prev_phase,
                bid_type='song'
            )
        
        elif prev_phase.action_type == 'create_chart':
            from .models import Chart
            return Chart.objects.filter(
                # 根据前一阶段的时间范围筛选
                created_at__gte=prev_phase.start_time,
                created_at__lte=prev_phase.end_time
            )
        
        elif prev_phase.action_type == 'allocate_chart':
            from .models import BidResult
            return BidResult.objects.filter(
                bidding_round__competition_phase=prev_phase,
                bid_type='chart'
            )
        
        return None
    
    def execute(self):
        """
        执行系统阶段（仅 execution_type='system_execute' 时调用）
        """
        if self.execution_type != 'system_execute':
            raise ValueError('只能执行 system_execute 类型的阶段')
        
        handler = PhaseExecutor.get_executor(self.action_type)
        return handler.execute(self)
```

---

### 2️⃣ PhaseExecutor（简化版 Handler）

```python
# songs/phase_executors.py

from abc import ABC, abstractmethod

class PhaseExecutor(ABC):
    """阶段执行器基类（仅处理系统执行的阶段）"""
    
    @abstractmethod
    def execute(self, phase):
        """执行阶段逻辑"""
        pass


class AllocateSongExecutor(PhaseExecutor):
    """歌曲竞标分配执行器"""
    
    def execute(self, phase):
        """执行歌曲竞标分配"""
        from .models import Bid, BidResult, BiddingRound
        from .bidding_service import BiddingService
        
        # 获取竞标轮次（基于 phase 创建或获取）
        bidding_round, created = BiddingRound.objects.get_or_create(
            competition_phase=phase,
            defaults={
                'name': phase.name,
                'bidding_type': 'song',
                'status': 'active'
            }
        )
        
        # 执行分配
        results = BiddingService.allocate_bids(
            bidding_round_id=bidding_round.id,
            priority_self=phase.config.get('priority_self', False)
        )
        
        # 标记轮次为已完成
        bidding_round.status = 'completed'
        bidding_round.save()
        
        return results


class AllocateChartExecutor(PhaseExecutor):
    """谱面竞标分配执行器"""
    
    def execute(self, phase):
        """执行谱面竞标分配"""
        from .models import Bid, BidResult, BiddingRound
        from .bidding_service import BiddingService
        
        bidding_round, created = BiddingRound.objects.get_or_create(
            competition_phase=phase,
            defaults={
                'name': phase.name,
                'bidding_type': 'chart',
                'status': 'active'
            }
        )
        
        results = BiddingService.allocate_bids(
            bidding_round_id=bidding_round.id,
            priority_self=phase.config.get('priority_self', True)  # 谱面竞标默认优先分配自己的
        )
        
        bidding_round.status = 'completed'
        bidding_round.save()
        
        return results


class AllocateReviewExecutor(PhaseExecutor):
    """互评任务分配执行器"""
    
    def execute(self, phase):
        """执行互评任务分配"""
        from .models import Chart, PeerReviewAllocation
        from django.contrib.auth.models import User
        import random
        
        config = phase.config
        reviews_per_user = config.get('reviews_per_user', 8)
        
        # 获取待评谱面（来自前置阶段）
        charts_to_review = phase.get_source_data()
        if not charts_to_review:
            raise ValueError('没有可评谱面')
        
        charts_list = list(charts_to_review)
        
        # 获取评分者（所有参赛用户）
        participants = User.objects.filter(
            charts__in=charts_list
        ).distinct()
        
        # 平衡分配算法（复用现有逻辑）
        allocations = []
        for reviewer in participants:
            # 排除自己的谱面
            available_charts = [c for c in charts_list if c.user != reviewer]
            
            # 随机选择 N 个
            selected = random.sample(
                available_charts,
                min(reviews_per_user, len(available_charts))
            )
            
            for chart in selected:
                allocations.append(
                    PeerReviewAllocation(
                        reviewer=reviewer,
                        chart=chart,
                        status='pending'
                    )
                )
        
        # 批量创建
        PeerReviewAllocation.objects.bulk_create(allocations)
        
        return {
            'total_allocations': len(allocations),
            'participants': participants.count(),
            'charts_count': len(charts_list),
        }


class PhaseExecutor:
    """执行器工厂"""
    
    _executors = {
        'allocate_song': AllocateSongExecutor(),
        'allocate_chart': AllocateChartExecutor(),
        'allocate_review': AllocateReviewExecutor(),
    }
    
    @classmethod
    def get_executor(cls, action_type):
        executor = cls._executors.get(action_type)
        if not executor:
            raise ValueError(f'未找到执行器: {action_type}')
        return executor
```

---

### 3️⃣ Collection + Phase 完整示例（解决用户提出的两个问题）

#### 问题1：如何让后台配置在前端直接拉取？

**后端配置**：
```python
# 创建阶段时，将所有限制放在config中
phase = Phase.objects.create(
    name='歌曲上传期',
    action_type='upload_song',
    config={
        'max_uploads': 3,                    # 最多上传数
        'allowed_formats': ['mp3', 'wav'],   # 允许的格式
        'max_file_size_mb': 10,              # 最大文件大小
        'min_duration_sec': 60,              # 最短时长
        'max_duration_sec': 300,             # 最长时长
    }
)
```

**前端调用**：
```javascript
// 前端只需调用一个API，获取所有配置
const { data: config } = await api.get('/api/songs/phase/config/')

// 返回示例：
// {
//   "phase_id": 1,
//   "phase_name": "歌曲上传期",
//   "action_type": "upload_song",
//   "can_participate": true,
//   "max_uploads": 3,              ← 后台配置直接返回
//   "allowed_formats": ["mp3", "wav"],
//   "max_file_size_mb": 10,
//   ...
// }

// 前端动态使用配置
if (uploadedCount >= config.max_uploads) {
  ElMessage.error(`最多只能上传 ${config.max_uploads} 首歌曲`)
}

if (!config.allowed_formats.includes(file.type)) {
  ElMessage.error(`仅支持格式：${config.allowed_formats.join(', ')}`)
}
```

#### 问题2：如何限制用户必须存在于上一个Collection？

**完整流程示例（带Collection和权限限制）**：

```python
# ===== 步骤1：创建Collections（数据集合定义）=====

# Collection 1：上传的歌曲
uploaded_songs = Collection.objects.create(
    name='2026春季上传歌曲',
    collection_type='uploaded_songs',
    query_filter={}  # 空过滤器 = 所有歌曲
)

# Collection 2：分配的歌曲（BidResult）
allocated_songs = Collection.objects.create(
    name='2026春季分配歌曲',
    collection_type='allocated_songs',
    query_filter={}
)

# Collection 3：提交的谱面
submitted_charts = Collection.objects.create(
    name='2026春季谱面',
    collection_type='submitted_charts',
    query_filter={'status': 'submitted'}  # 只包含已提交的
)

# Collection 4：互评任务
peer_review_tasks = Collection.objects.create(
    name='2026春季互评',
    collection_type='peer_reviews',
    query_filter={}
)

# ===== 步骤2：创建Phases（带Collection关联和权限限制）=====

# Phase 1：上传歌曲
phase1 = Phase.objects.create(
    name='歌曲上传期',
    phase_category='song',
    execution_type='user_action',
    action_type='upload_song',
    
    # Collection关联
    input_collection=None,  # 无输入限制，所有人都可以上传
    output_collection=uploaded_songs,  # 产出数据进入uploaded_songs
    require_in_input_collection=False,  # 不限制参与者
    
    config={
        'max_uploads': 3,
        'allowed_formats': ['mp3'],
    }
)

# Phase 2：竞标歌曲
phase2 = Phase.objects.create(
    name='歌曲竞标期',
    phase_category='song',
    execution_type='user_action',
    action_type='bid_song',
    
    # Collection关联
    input_collection=uploaded_songs,  # 可竞标的歌曲来自uploaded_songs
    output_collection=uploaded_songs,  # 竞标数据关联到现有歌曲（不产生新Collection）
    require_in_input_collection=False,  # 不要求必须上传过歌曲才能竞标
    
    config={
        'max_bids': 5,
    }
)

# Phase 3：分配歌曲（系统执行）
phase3 = Phase.objects.create(
    name='歌曲分配',
    phase_category='song',
    execution_type='system_execute',
    action_type='allocate_song',
    
    # Collection关联
    input_collection=uploaded_songs,  # 基于上传的歌曲分配
    output_collection=allocated_songs,  # 产出分配结果
    
    config={'random_cost': 200}
)

# Phase 4：制谱（关键：限制只有获得分配的用户才能参与）
phase4 = Phase.objects.create(
    name='制谱期',
    phase_category='chart',
    execution_type='user_action',
    action_type='create_chart',
    
    # Collection关联
    input_collection=allocated_songs,  # 基于分配结果
    output_collection=submitted_charts,  # 产出谱面
    require_in_input_collection=True,  # ← 关键：必须在allocated_songs中
    
    config={
        'is_partial': False,
        'required_files': ['maidata.txt'],
    }
)

# Phase 5：互评（关键：限制只有提交谱面的用户才能参与）
phase5_allocate = Phase.objects.create(
    name='互评任务分配',
    phase_category='review',
    execution_type='system_execute',
    action_type='allocate_review',
    
    input_collection=submitted_charts,  # 基于提交的谱面
    output_collection=peer_review_tasks,  # 产出互评任务
    
    config={'reviews_per_user': 8}
)

phase5_review = Phase.objects.create(
    name='互评期',
    phase_category='review',
    execution_type='user_action',
    action_type='peer_review',
    
    input_collection=peer_review_tasks,  # 基于分配的任务
    output_collection=peer_review_tasks,  # 评分数据更新到现有集合
    require_in_input_collection=True,  # ← 必须有互评任务才能评分
    
    config={'max_score': 50}
)
```

**权限检查效果演示**：

```python
# 用户A上传了歌曲并获得了分配 → 可以参与制谱
user_a = User.objects.get(username='user_a')
can_participate, msg = phase4.can_user_participate(user_a)
# 返回: (True, '')

# 用户B没有获得分配 → 无法参与制谱
user_b = User.objects.get(username='user_b')
can_participate, msg = phase4.can_user_participate(user_b)
# 返回: (False, '您不在参与者名单中（需要在"2026春季分配歌曲"集合中）')

# 前端调用API时会自动检查权限
# GET /api/songs/phase/info/
# → 如果user_b调用，返回403错误和msg
```

---

### 4️⃣ 实际使用示例（更新版）

#### 示例1：传统流程（完整版）

```python
# 阶段1：上传歌曲（用户操作）
phase1 = Phase.objects.create(
    name='歌曲上传期',
    phase_category='song',
    execution_type='user_action',
    action_type='upload_song',
    order=1,
    start_time='2026-02-01 00:00',
    end_time='2026-02-07 23:59',
    config={
        'max_uploads': 3,
        'allowed_formats': ['mp3'],
        'max_file_size_mb': 10,
    }
)

# 阶段2：竞标歌曲（用户操作）
phase2 = Phase.objects.create(
    name='歌曲竞标期',
    phase_category='song',
    execution_type='user_action',
    action_type='bid_song',
    depends_on=phase1,  # 依赖歌曲上传
    order=2,
    start_time='2026-02-08 00:00',
    end_time='2026-02-14 23:59',
    config={
        'max_bids': 5,
    }
)

# 阶段3：分配歌曲（系统执行）
phase3 = Phase.objects.create(
    name='歌曲分配',
    phase_category='song',
    execution_type='system_execute',
    action_type='allocate_song',
    depends_on=phase2,  # 依赖竞标数据
    order=3,
    start_time='2026-02-14 23:59',
    end_time='2026-02-15 00:00',  # 瞬时执行
    config={
        'random_cost': 200,
        'priority_self': False,
    }
)

# 阶段4：制谱（第一阶段）
phase4 = Phase.objects.create(
    name='制谱期（第一阶段）',
    phase_category='chart',
    execution_type='user_action',
    action_type='create_chart',
    depends_on=phase3,  # 依赖分配结果
    order=4,
    start_time='2026-02-15 00:00',
    end_time='2026-02-28 23:59',
    config={
        'is_partial': True,  # 半成品
        'required_files': ['maidata.txt', 'audio.mp3', 'cover.jpg'],
    }
)

# 阶段5：竞标谱面
phase5 = Phase.objects.create(
    name='谱面竞标期',
    phase_category='chart',
    execution_type='user_action',
    action_type='bid_chart',
    depends_on=phase4,
    order=5,
    start_time='2026-03-01 00:00',
    end_time='2026-03-07 23:59',
    config={
        'max_bids': 5,
        'allow_self_bidding': True,
    }
)

# 阶段6：分配谱面
phase6 = Phase.objects.create(
    name='谱面分配',
    phase_category='chart',
    execution_type='system_execute',
    action_type='allocate_chart',
    depends_on=phase5,
    order=6,
    start_time='2026-03-07 23:59',
    end_time='2026-03-08 00:00',
    config={
        'random_cost': 200,
        'priority_self': True,
    }
)

# 阶段7：完成谱面
phase7 = Phase.objects.create(
    name='制谱期（第二阶段）',
    phase_category='chart',
    execution_type='user_action',
    action_type='create_chart',
    depends_on=phase6,
    order=7,
    start_time='2026-03-08 00:00',
    end_time='2026-03-21 23:59',
    config={
        'is_partial': False,  # 完整版
    }
)

# 阶段8：分配互评任务（系统执行）
phase8 = Phase.objects.create(
    name='互评任务分配',
    phase_category='review',
    execution_type='system_execute',
    action_type='allocate_review',
    depends_on=phase7,
    order=8,
    start_time='2026-03-21 23:59',
    end_time='2026-03-22 00:00',
    config={
        'reviews_per_user': 8,
    }
)

# 阶段9：互评
phase9 = Phase.objects.create(
    name='互评期',
    phase_category='review',
    execution_type='user_action',
    action_type='peer_review',
    depends_on=phase8,
    order=9,
    start_time='2026-03-22 00:00',
    end_time='2026-04-05 23:59',
    config={
        'max_score': 50,
    }
)
```

#### 示例2：快速赛（跳过竞标）

```python
# 阶段1：上传歌曲
phase1 = Phase.objects.create(
    name='歌曲上传期',
    phase_category='song',
    execution_type='user_action',
    action_type='upload_song',
    order=1,
    start_time='2026-02-01 00:00',
    end_time='2026-02-03 23:59',
    config={'max_uploads': 1}
)

# 阶段2：直接制谱（基于自己上传的歌曲）
phase2 = Phase.objects.create(
    name='制谱期',
    phase_category='chart',
    execution_type='user_action',
    action_type='create_chart',
    depends_on=phase1,  # 基于上传的歌曲
    order=2,
    start_time='2026-02-04 00:00',
    end_time='2026-02-10 23:59',
    config={
        'is_partial': False,
        'create_for_own_song': True,  # 为自己的歌曲制谱
    }
)

# 阶段3：分配互评
phase3 = Phase.objects.create(
    name='互评任务分配',
    phase_category='review',
    execution_type='system_execute',
    action_type='allocate_review',
    depends_on=phase2,
    order=3,
    start_time='2026-02-10 23:59',
    end_time='2026-02-11 00:00',
    config={'reviews_per_user': 5}
)

# 阶段4：互评
phase4 = Phase.objects.create(
    name='互评期',
    phase_category='review',
    execution_type='user_action',
    action_type='peer_review',
    depends_on=phase3,
    order=4,
    start_time='2026-02-11 00:00',
    end_time='2026-02-17 23:59',
    config={'max_score': 50}
)
```

#### 示例3：多轮制谱

```python
# 上传 → 竞标1 → 分配1 → 制谱1 → 竞标2 → 分配2 → 制谱2 → 竞标3 → 分配3 → 制谱3 → 互评

# ... 省略前三个阶段（上传、竞标、分配）

# 第一轮制谱
phase4 = Phase.objects.create(
    name='第一轮制谱',
    phase_category='chart',
    execution_type='user_action',
    action_type='create_chart',
    depends_on=phase3,
    order=4,
    config={'is_partial': True, 'part_number': 1}
)

# 第二轮竞标谱面
phase5 = Phase.objects.create(
    name='第二轮竞标',
    phase_category='chart',
    execution_type='user_action',
    action_type='bid_chart',
    depends_on=phase4,
    order=5,
)

# 第二轮分配
phase6 = Phase.objects.create(
    name='第二轮分配',
    phase_category='chart',
    execution_type='system_execute',
    action_type='allocate_chart',
    depends_on=phase5,
    order=6,
)

# 第二轮制谱
phase7 = Phase.objects.create(
    name='第二轮制谱',
    phase_category='chart',
    execution_type='user_action',
    action_type='create_chart',
    depends_on=phase6,
    order=7,
    config={'is_partial': True, 'part_number': 2}
)

# 第三轮竞标
phase8 = Phase.objects.create(
    name='第三轮竞标',
    phase_category='chart',
    execution_type='user_action',
    action_type='bid_chart',
    depends_on=phase7,
    order=8,
)

# 第三轮分配
phase9 = Phase.objects.create(
    name='第三轮分配',
    phase_category='chart',
    execution_type='system_execute',
    action_type='allocate_chart',
    depends_on=phase8,
    order=9,
)

# 第三轮制谱（完成）
phase10 = Phase.objects.create(
    name='第三轮制谱（完成）',
    phase_category='chart',
    execution_type='user_action',
    action_type='create_chart',
    depends_on=phase9,
    order=10,
    config={'is_partial': False}
)

# 互评
phase11 = Phase.objects.create(
    name='互评任务分配',
    phase_category='review',
    execution_type='system_execute',
    action_type='allocate_review',
    depends_on=phase10,
    order=11,
)

phase12 = Phase.objects.create(
    name='互评期',
    phase_category='review',
    execution_type='user_action',
    action_type='peer_review',
    depends_on=phase11,
    order=12,
)
```

---

### 4️⃣ 前端适配（最小改动）

#### API 更新

```python
# views.py

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_competition_status(request):
    """获取当前比赛状态（兼容旧 API）"""
    from django.utils import timezone
    now = timezone.now()
    
    # 获取当前活跃阶段
    current_phase = Phase.objects.filter(
        is_active=True,
        start_time__lte=now,
        end_time__gte=now
    ).first()
    
    if not current_phase:
        # 返回默认状态
        return Response({
            'currentRound': '未开始',
            'status': 'pending',
            'participants': 0,
            'submissions': 0,
        })
    
    # 根据 phase_category 统计数据
    if current_phase.phase_category == 'song':
        from .models import Song
        submissions = Song.objects.count()
        label = '歌曲数'
    elif current_phase.phase_category == 'chart':
        from .models import Chart
        submissions = Chart.objects.count()
        label = '谱面数'
    else:  # review
        from .models import Chart
        submissions = Chart.objects.filter(status='submitted').count()
        label = '待评谱面数'
    
    # 返回数据
    return Response({
        'currentRound': current_phase.name,
        'status': current_phase.status,
        'statusText': {
            'upcoming': '即将开始',
            'active': '进行中',
            'ended': '已结束',
        }.get(current_phase.status, '未知'),
        'participants': User.objects.filter(is_active=True).count(),
        'submissions': submissions,
        'submissionsLabel': label,
        'phaseKey': current_phase.action_type,  # 新：使用 action_type
        'phaseCategory': current_phase.phase_category,  # 新：分类
        'executionType': current_phase.execution_type,  # 新：执行类型
        'startTime': current_phase.start_time,
        'endTime': current_phase.end_time,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_phase_config(request):
    """
    获取当前阶段的完整配置（供前端动态渲染）
    前端可直接使用返回的配置，无需硬编码
    """
    current_phase = Phase.objects.filter(
        is_active=True,
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now()
    ).first()
    
    if not current_phase:
        return Response({'error': '没有活跃阶段'}, status=404)
    
    # 返回完整配置（包含max_uploads, max_bids等所有后台配置）
    config = current_phase.get_user_action_config(request.user)
    
    return Response(config)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_phase_info(request):
    """获取用户在当前阶段的操作信息（含数据）"""
    current_phase = Phase.objects.filter(
        is_active=True,
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now()
    ).first()
    
    if not current_phase:
        return Response({'error': '没有活跃阶段'}, status=404)
    
    user = request.user
    
    # ========== 新增：权限检查 ==========
    can_participate, error_msg = current_phase.can_user_participate(user)
    if not can_participate:
        return Response({
            'error': error_msg,
            'can_participate': False,
        }, status=403)
    # ===================================
    
    # 根据 action_type 返回不同的操作信息
    if current_phase.action_type == 'upload_song':
        from .models import Song
        uploaded = Song.objects.filter(user=user).count()
        max_uploads = current_phase.config.get('max_uploads', 3)
        
        return Response({
            'action': 'upload_song',
            'uploaded_count': uploaded,
            'max_uploads': max_uploads,
            'can_upload': uploaded < max_uploads,
        })
    
    elif current_phase.action_type == 'bid_song':
        from .models import Bid
        bids = Bid.objects.filter(
            user=user,
            bidding_round__competition_phase=current_phase,
            is_dropped=False
        )
        max_bids = current_phase.config.get('max_bids', 5)
        
        return Response({
            'action': 'bid_song',
            'bid_count': bids.count(),
            'max_bids': max_bids,
            'can_bid': bids.count() < max_bids,
            'bids': BidSerializer(bids, many=True).data,
        })
    
    elif current_phase.action_type == 'create_chart':
        from .models import BidResult, Chart
        
        # 获取用户的分配结果
        if current_phase.depends_on:
            allocations = BidResult.objects.filter(
                user=user,
                bidding_round__competition_phase=current_phase.depends_on
            )
        else:
            # 没有前置阶段，基于自己上传的歌曲
            allocations = None
        
        # 检查是否已提交
        charts = Chart.objects.filter(
            user=user,
            created_at__gte=current_phase.start_time,
            created_at__lte=current_phase.end_time
        )
        
        return Response({
            'action': 'create_chart',
            'allocations': BidResultSerializer(allocations, many=True).data if allocations else [],
            'submitted_charts': ChartSerializer(charts, many=True).data,
            'can_submit': allocations.exists() if allocations else True,
        })
    
    elif current_phase.action_type == 'peer_review':
        from .models import PeerReviewAllocation
        
        allocations = PeerReviewAllocation.objects.filter(reviewer=user)
        pending = allocations.filter(status='pending')
        
        return Response({
            'action': 'peer_review',
            'total_tasks': allocations.count(),
            'pending_tasks': pending.count(),
            'max_score': current_phase.config.get('max_score', 50),
        })
    
    return Response({'error': '未知的阶段类型'}, status=400)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def execute_phase(request, phase_id):
    """执行系统阶段（管理员专用）"""
    phase = get_object_or_404(Phase, id=phase_id)
    
    if phase.execution_type != 'system_execute':
        return Response(
            {'error': '只能执行 system_execute 类型的阶段'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if phase.status != 'ended':
        return Response(
            {'error': '只能对已结束的阶段执行'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        results = phase.execute()
        return Response({
            'success': True,
            'results': results,
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

#### 前端适配（完全动态化，后台配置驱动）

```javascript
// ===== 方式1：获取阶段配置（推荐：后台配置直接拉取）=====

const { data: config } = await api.get('/api/songs/phase/config/')

// 返回完整配置，前端无需硬编码任何限制
console.log(config)
// {
//   "phase_id": 1,
//   "phase_name": "歌曲上传期",
//   "phase_category": "song",
//   "action_type": "upload_song",
//   "can_participate": true,        ← 自动检查权限
//   "error_message": "",
//   "max_uploads": 3,               ← 后台配置
//   "allowed_formats": ["mp3"],     ← 后台配置
//   "max_file_size_mb": 10,         ← 后台配置
//   "status": "active",
//   "start_time": "2026-02-01T00:00:00",
//   "end_time": "2026-02-07T23:59:59"
// }

// 前端动态渲染
if (!config.can_participate) {
  ElMessage.error(config.error_message)
  return
}

// 动态使用后台配置
<el-upload 
  :limit="config.max_uploads"
  :accept="config.allowed_formats.map(f => `.${f}`).join(',')"
  :file-size-limit="config.max_file_size_mb * 1024 * 1024"
>
  <el-button>上传歌曲 (已上传 {{ uploadedCount }} / {{ config.max_uploads }})</el-button>
</el-upload>

// 动态验证
const validateFile = (file) => {
  if (!config.allowed_formats.some(fmt => file.name.endsWith(`.${fmt}`))) {
    ElMessage.error(`仅支持格式：${config.allowed_formats.join(', ')}`)
    return false
  }
  
  if (file.size > config.max_file_size_mb * 1024 * 1024) {
    ElMessage.error(`文件大小不能超过 ${config.max_file_size_mb}MB`)
    return false
  }
  
  return true
}


// ===== 方式2：获取当前比赛状态（兼容旧版）=====

const { data: status } = await api.get('/api/songs/status/')

// 根据 phase_category 控制页面访问
if (status.phaseCategory === 'song') {
  router.push('/songs')
} else if (status.phaseCategory === 'chart') {
  router.push('/charts')
} else if (status.phaseCategory === 'review') {
  router.push('/eval')
}


// ===== 方式3：获取用户操作信息（含数据）=====

const { data: info } = await api.get('/api/songs/phase/info/')

// 如果用户没有权限，会返回403
if (info.can_participate === false) {
  ElMessage.error(info.error_message)
  return
}

// 根据action_type显示对应数据
if (info.action === 'upload_song') {
  console.log(`已上传 ${info.uploaded_count} / ${info.max_uploads}`)
} else if (info.action === 'bid_song') {
  displayBids(info.bids)
} else if (info.action === 'create_chart') {
  displayAllocations(info.allocations)
}
```

**核心优势**：
✅ **前端无硬编码**：所有限制（max_uploads, max_bids等）都从后台拉取  
✅ **权限自动检查**：`can_participate`字段自动验证用户是否在required collection中  
✅ **配置集中管理**：修改限制只需更新Phase.config，前端无需改代码  
✅ **错误信息友好**：`error_message`直接返回可显示的错误提示

---

## 🚀 实施路线图（V2.5混合架构）

> **总耗时预估**: 2-3周  
> **风险等级**: 低（渐进式改造，可灰度发布）

---

### 📋 准备阶段（1天）

#### 1. 环境准备

```bash
# 1. 创建新分支
git checkout -b feature/v2.5-architecture

# 2. 备份数据库
python manage.py dumpdata songs > backup_songs_$(date +%Y%m%d).json
# 或使用PostgreSQL dump
pg_dump xmmcg_db > backup_$(date +%Y%m%d).sql

# 3. 创建测试环境
cp .env .env.backup
# 配置测试数据库
```

#### 2. 代码审查清单

- [ ] 确认现有CompetitionPhase模型字段
- [ ] 确认phase_key的所有使用位置（grep搜索）
- [ ] 确认前端API调用位置
- [ ] 准备回滚计划

---

### 🗄️ 阶段1：数据库迁移（3-5天）

#### 步骤1.1：创建Collection模型（1天）

**文件**：`backend/xmmcg/songs/models.py`

```python
# 在CompetitionPhase模型之前添加

class Collection(models.Model):
    """数据集合（轻量级，不存储实际数据，只存储查询条件）"""
    
    COLLECTION_TYPE_CHOICES = [
        ('uploaded_songs', '上传的歌曲'),
        ('allocated_songs', '分配的歌曲（BidResult）'),
        ('submitted_charts', '提交的谱面'),
        ('allocated_charts', '分配的谱面（BidResult）'),
        ('peer_reviews', '互评评分'),
    ]
    
    name = models.CharField(max_length=100, help_text='集合名称，如"2026春季上传歌曲"')
    collection_type = models.CharField(
        max_length=30,
        choices=COLLECTION_TYPE_CHOICES,
        help_text='集合类型（决定查询哪个模型）'
    )
    query_filter = models.JSONField(
        default=dict,
        help_text='查询过滤条件，如 {"status": "submitted", "created_at__gte": "2026-02-01"}'
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '数据集合'
        verbose_name_plural = '数据集合'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_collection_type_display()})"
    
    def get_queryset(self):
        """根据 collection_type 和 query_filter 返回 QuerySet"""
        if self.collection_type == 'uploaded_songs':
            from .models import Song
            qs = Song.objects.all()
        elif self.collection_type == 'allocated_songs':
            from .models import BidResult
            qs = BidResult.objects.filter(bid_type='song')
        elif self.collection_type == 'submitted_charts':
            from .models import Chart
            qs = Chart.objects.all()
        elif self.collection_type == 'allocated_charts':
            from .models import BidResult
            qs = BidResult.objects.filter(bid_type='chart')
        elif self.collection_type == 'peer_reviews':
            from .models import PeerReview
            qs = PeerReview.objects.all()
        else:
            return None
        
        if self.query_filter:
            qs = qs.filter(**self.query_filter)
        
        return qs
    
    def count(self):
        """统计数量"""
        qs = self.get_queryset()
        return qs.count() if qs else 0
    
    def contains_user(self, user):
        """检查用户是否在此Collection中（用于参与限制）"""
        qs = self.get_queryset()
        if not qs:
            return False
        
        if self.collection_type in ['uploaded_songs', 'submitted_charts']:
            return qs.filter(user=user).exists()
        elif self.collection_type in ['allocated_songs', 'allocated_charts']:
            return qs.filter(user=user).exists()
        elif self.collection_type == 'peer_reviews':
            return qs.filter(reviewer=user).exists()
        
        return False
```

#### 步骤1.2：生成Collection迁移文件（1天）

```bash
# 生成迁移
python manage.py makemigrations songs --name add_collection_model

# 预览SQL（不执行）
python manage.py sqlmigrate songs 0XXX

# 执行迁移
python manage.py migrate songs

# 验证
python manage.py shell
>>> from songs.models import Collection
>>> Collection.objects.create(name='测试', collection_type='uploaded_songs')
```

#### 步骤1.3：扩展CompetitionPhase模型（2天）

**文件**：`backend/xmmcg/songs/models.py`

在CompetitionPhase类中添加字段：

```python
class CompetitionPhase(models.Model):
    # ... 保留原有字段 ...
    
    # ========== V2.5新增字段 ==========
    
    # 阶段分类
    PHASE_CATEGORY_CHOICES = [
        ('song', '歌曲相关'),
        ('chart', '谱面相关'),
        ('review', '评价相关'),
    ]
    phase_category = models.CharField(
        max_length=20,
        choices=PHASE_CATEGORY_CHOICES,
        default='song',
        help_text='阶段类别（决定前端页面）',
        db_index=True
    )
    
    # 执行类型
    EXECUTION_TYPE_CHOICES = [
        ('user_action', '用户操作'),
        ('system_execute', '系统执行'),
    ]
    execution_type = models.CharField(
        max_length=20,
        choices=EXECUTION_TYPE_CHOICES,
        default='user_action',
        help_text='执行类型'
    )
    
    # 阶段动作
    ACTION_TYPE_CHOICES = [
        ('upload_song', '上传歌曲'),
        ('bid_song', '竞标歌曲'),
        ('allocate_song', '分配歌曲'),
        ('create_chart', '制作谱面'),
        ('bid_chart', '竞标谱面'),
        ('allocate_chart', '分配谱面'),
        ('peer_review', '互评'),
        ('allocate_review', '分配评分任务'),
        ('judge_review', '评委评分'),
        ('voting', '用户投票'),
    ]
    action_type = models.CharField(
        max_length=30,
        choices=ACTION_TYPE_CHOICES,
        help_text='具体动作类型'
    )
    
    # Collection关联
    input_collection = models.ForeignKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consuming_phases',
        help_text='输入数据集合'
    )
    
    output_collection = models.ForeignKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='producing_phases',
        help_text='输出数据集合'
    )
    
    # 参与限制
    require_in_input_collection = models.BooleanField(
        default=False,
        help_text='是否要求用户必须存在于input_collection中'
    )
    
    # 依赖关系
    depends_on = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dependent_phases',
        help_text='依赖的前置阶段'
    )
    
    # ========== 新增方法 ==========
    
    def can_user_participate(self, user):
        """检查用户是否可以参与此阶段"""
        if self.status != 'active':
            return False, f'阶段未开放（当前：{self.status}）'
        
        if self.require_in_input_collection and self.input_collection:
            if not self.input_collection.contains_user(user):
                return False, f'您不在参与者名单中（需要在"{self.input_collection.name}"中）'
        
        return True, ''
    
    def get_user_action_config(self, user):
        """获取用户可用的操作配置（供前端使用）"""
        can_participate, error_msg = self.can_user_participate(user)
        
        base_config = {
            'phase_id': self.id,
            'phase_name': self.name,
            'phase_category': self.phase_category,
            'action_type': self.action_type,
            'execution_type': self.execution_type,
            'can_participate': can_participate,
            'error_message': error_msg,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'page_access': self.page_access,
        }
        
        base_config.update(self.config)
        return base_config
```

#### 步骤1.4：生成Phase扩展迁移（含数据迁移）

```bash
# 生成迁移
python manage.py makemigrations songs --name extend_phase_v25
```

**手动编辑迁移文件**，添加数据迁移逻辑：

```python
# migrations/0XXX_extend_phase_v25.py

def migrate_existing_phases(apps, schema_editor):
    """根据phase_key推断新字段值"""
    Phase = apps.get_model('songs', 'CompetitionPhase')
    
    mapping = {
        'upload': ('song', 'user_action', 'upload_song'),
        'bidding': ('song', 'user_action', 'bid_song'),
        'allocation': ('song', 'system_execute', 'allocate_song'),
        'mapping1': ('chart', 'user_action', 'create_chart'),
        'chart_bidding': ('chart', 'user_action', 'bid_chart'),
        'chart_allocation': ('chart', 'system_execute', 'allocate_chart'),
        'mapping2': ('chart', 'user_action', 'create_chart'),
        'peer_review': ('review', 'user_action', 'peer_review'),
    }
    
    for phase in Phase.objects.all():
        for key, (cat, exec_type, act) in mapping.items():
            if key in phase.phase_key.lower():
                phase.phase_category = cat
                phase.execution_type = exec_type
                phase.action_type = act
                phase.save()
                break

class Migration(migrations.Migration):
    operations = [
        # ... AddField operations ...
        migrations.RunPython(migrate_existing_phases),
    ]
```

```bash
# 执行迁移
python manage.py migrate songs

# 验证
python manage.py shell
>>> from songs.models import CompetitionPhase
>>> for p in CompetitionPhase.objects.all():
...     print(f"{p.name}: {p.phase_category}, {p.action_type}")
```

---

### 💻 阶段2：后端API实现（1周）

#### 步骤2.1：添加新API端点（2天）

**文件**：`backend/xmmcg/songs/views.py`

```python
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_phase_config(request):
    """获取当前阶段的完整配置（供前端动态渲染）"""
    from django.utils import timezone
    current_phase = CompetitionPhase.objects.filter(
        is_active=True,
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now()
    ).first()
    
    if not current_phase:
        return Response({'error': '没有活跃阶段'}, status=404)
    
    config = current_phase.get_user_action_config(request.user)
    return Response(config)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_phase_info(request):
    """获取用户在当前阶段的操作信息（含数据）"""
    from django.utils import timezone
    current_phase = CompetitionPhase.objects.filter(
        is_active=True,
        start_time__lte=timezone.now(),
        end_time__gte=timezone.now()
    ).first()
    
    if not current_phase:
        return Response({'error': '没有活跃阶段'}, status=404)
    
    # 权限检查
    can_participate, error_msg = current_phase.can_user_participate(request.user)
    if not can_participate:
        return Response({
            'error': error_msg,
            'can_participate': False,
        }, status=403)
    
    # 根据action_type返回对应数据
    # ... (参考文档中的完整实现)
    
    return Response(data)
```

**文件**：`backend/xmmcg/songs/urls.py`

```python
urlpatterns = [
    # ... 现有路由 ...
    
    # 新增V2.5端点
    path('phase/config/', views.get_phase_config, name='phase-config'),
    path('phase/info/', views.get_user_phase_info, name='phase-info'),
]
```

#### 步骤2.2：实现PhaseExecutor（2天）

**新文件**：`backend/xmmcg/songs/phase_executors.py`

```python
from abc import ABC, abstractmethod

class PhaseExecutor(ABC):
    @abstractmethod
    def execute(self, phase):
        pass

class AllocateSongExecutor(PhaseExecutor):
    def execute(self, phase):
        from .models import BiddingRound
        from .bidding_service import BiddingService
        
        bidding_round = BiddingRound.objects.get(competition_phase=phase)
        results = BiddingService.allocate_bids(
            bidding_round_id=bidding_round.id,
            priority_self=phase.config.get('priority_self', False)
        )
        return results

# ... 其他Executor实现 ...

# 工厂类
class PhaseExecutorFactory:
    _executors = {
        'allocate_song': AllocateSongExecutor(),
        'allocate_chart': AllocateChartExecutor(),
        'allocate_review': AllocateReviewExecutor(),
    }
    
    @classmethod
    def get_executor(cls, action_type):
        return cls._executors.get(action_type)
```

在`CompetitionPhase`模型中添加：

```python
def execute(self):
    """执行系统阶段"""
    if self.execution_type != 'system_execute':
        raise ValueError('只能执行system_execute类型的阶段')
    
    from .phase_executors import PhaseExecutorFactory
    executor = PhaseExecutorFactory.get_executor(self.action_type)
    if not executor:
        raise ValueError(f'未找到执行器: {self.action_type}')
    
    return executor.execute(self)
```

#### 步骤2.3：更新现有API兼容性（1天）

确保现有前端代码继续工作：

```python
# views.py - 更新get_competition_status
def get_competition_status(request):
    # ... 现有逻辑 ...
    
    return Response({
        # 保留旧字段
        'currentRound': current_phase.name,
        'phaseKey': current_phase.phase_key,  # 兼容旧版
        
        # 添加新字段
        'phaseCategory': current_phase.phase_category,
        'actionType': current_phase.action_type,
        'executionType': current_phase.execution_type,
    })
```

#### 步骤2.4：编写单元测试（2天）

**新文件**：`backend/xmmcg/songs/tests/test_collection.py`

```python
from django.test import TestCase
from songs.models import Collection, Song, Chart

class CollectionTestCase(TestCase):
    def test_collection_queryset(self):
        # 创建测试数据
        song1 = Song.objects.create(title='Test Song')
        
        # 创建Collection
        col = Collection.objects.create(
            name='Test Collection',
            collection_type='uploaded_songs',
            query_filter={}
        )
        
        # 测试get_queryset
        qs = col.get_queryset()
        self.assertIn(song1, qs)
    
    def test_contains_user(self):
        # ... 测试用户检查逻辑 ...
        pass
```

**新文件**：`backend/xmmcg/songs/tests/test_phase_v25.py`

```python
from django.test import TestCase
from songs.models import CompetitionPhase, Collection

class PhaseV25TestCase(TestCase):
    def test_can_user_participate(self):
        # 创建Collection
        col = Collection.objects.create(...)
        
        # 创建Phase（要求在Collection中）
        phase = CompetitionPhase.objects.create(
            input_collection=col,
            require_in_input_collection=True
        )
        
        # 测试用户权限
        can, msg = phase.can_user_participate(user)
        self.assertFalse(can)
    
    def test_get_user_action_config(self):
        # ... 测试配置拉取 ...
        pass
```

```bash
# 运行测试
python manage.py test songs.tests.test_collection
python manage.py test songs.tests.test_phase_v25
```

---

### 🎨 阶段3：管理后台（2-3天）

#### 步骤3.1：Collection管理界面（1天）

**文件**：`backend/xmmcg/songs/admin.py`

```python
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'collection_type', 'item_count', 'created_at']
    list_filter = ['collection_type', 'created_at']
    search_fields = ['name', 'description']
    
    fieldsets = [
        ('基本信息', {
            'fields': ['name', 'collection_type', 'description']
        }),
        ('查询条件', {
            'fields': ['query_filter'],
            'description': '使用Django ORM查询字典格式，如 {"status": "submitted"}'
        }),
    ]
    
    def item_count(self, obj):
        """显示集合项数量"""
        return obj.count()
    item_count.short_description = '项目数'
```

#### 步骤3.2：Phase管理界面增强（1-2天）

```python
@admin.register(CompetitionPhase)
class CompetitionPhaseAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'name', 'phase_category', 'action_type',
        'execution_type', 'status', 'start_time', 'end_time',
        'input_col', 'output_col'
    ]
    list_filter = [
        'phase_category', 'execution_type', 'action_type',
        'is_active', 'require_in_input_collection'
    ]
    search_fields = ['name', 'description', 'phase_key']
    ordering = ['order', 'start_time']
    
    fieldsets = [
        ('基本信息', {
            'fields': ['name', 'phase_key', 'description', 'order', 'is_active']
        }),
        ('阶段分类', {
            'fields': ['phase_category', 'execution_type', 'action_type']
        }),
        ('Collection关联（V2.5）', {
            'fields': [
                'input_collection',
                'output_collection',
                'require_in_input_collection'
            ],
            'description': 'Collection用于定义数据流向和参与限制'
        }),
        ('依赖关系', {
            'fields': ['depends_on']
        }),
        ('时间设置', {
            'fields': ['start_time', 'end_time']
        }),
        ('配置', {
            'fields': ['page_access', 'config'],
            'classes': ['collapse']
        }),
    ]
    
    def input_col(self, obj):
        return obj.input_collection.name if obj.input_collection else '-'
    input_col.short_description = '输入集合'
    
    def output_col(self, obj):
        return obj.output_collection.name if obj.output_collection else '-'
    output_col.short_description = '输出集合'
    
    # 自定义操作
    actions = ['execute_system_phases', 'create_collections_for_phases']
    
    def execute_system_phases(self, request, queryset):
        """批量执行系统阶段"""
        executed = 0
        for phase in queryset.filter(execution_type='system_execute'):
            if phase.status == 'ended':
                try:
                    phase.execute()
                    executed += 1
                except Exception as e:
                    self.message_user(request, f'执行{phase.name}失败: {e}', level='ERROR')
        
        self.message_user(request, f'成功执行 {executed} 个阶段', level='SUCCESS')
    
    execute_system_phases.short_description = '执行选中的系统阶段'
```

---

### 🌐 阶段4：前端适配（1-2天）

#### 步骤4.1：新增API调用（0.5天）

**文件**：`front/src/api/phase.js`（新建）

```javascript
import request from '@/utils/request'

// 获取当前阶段配置
export function getPhaseConfig() {
  return request({
    url: '/api/songs/phase/config/',
    method: 'get'
  })
}

// 获取用户阶段信息
export function getUserPhaseInfo() {
  return request({
    url: '/api/songs/phase/info/',
    method: 'get'
  })
}
```

#### 步骤4.2：动态配置使用（1天）

**文件**：`front/src/views/Songs.vue`

```vue
<script setup>
import { ref, onMounted } from 'vue'
import { getPhaseConfig } from '@/api/phase'
import { ElMessage } from 'element-plus'

const phaseConfig = ref({})
const uploadedCount = ref(0)

const loadConfig = async () => {
  try {
    const { data } = await getPhaseConfig()
    phaseConfig.value = data
    
    // 检查权限
    if (!data.can_participate) {
      ElMessage.error(data.error_message)
      return
    }
    
    // 使用后台配置
    console.log('最大上传数:', data.max_uploads)
    console.log('允许格式:', data.allowed_formats)
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const validateFile = (file) => {
  const config = phaseConfig.value
  
  // 动态检查格式
  if (!config.allowed_formats?.some(fmt => file.name.endsWith(`.${fmt}`))) {
    ElMessage.error(`仅支持: ${config.allowed_formats.join(', ')}`)
    return false
  }
  
  // 动态检查大小
  if (file.size > config.max_file_size_mb * 1024 * 1024) {
    ElMessage.error(`文件不能超过 ${config.max_file_size_mb}MB`)
    return false
  }
  
  return true
}

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <div v-if="phaseConfig.can_participate">
    <el-upload
      :limit="phaseConfig.max_uploads"
      :before-upload="validateFile"
    >
      <el-button>
        上传歌曲 ({{ uploadedCount }} / {{ phaseConfig.max_uploads }})
      </el-button>
    </el-upload>
  </div>
  <div v-else>
    <el-alert type="error" :title="phaseConfig.error_message" />
  </div>
</template>
```

#### 步骤4.3：兼容性测试（0.5天）

确保现有功能不受影响：

- [ ] 歌曲上传页面正常
- [ ] 竞标页面正常
- [ ] 制谱页面正常
- [ ] 互评页面正常
- [ ] 首页状态显示正常

---

### ✅ 阶段5：测试与验证（3天）

#### 步骤5.1：集成测试（1天）

**测试场景1：简化流程（无谱面竞标）**

```python
# 测试脚本: test_simple_flow.py

# 1. 创建Collections
uploaded_songs = Collection.objects.create(
    name='测试-上传歌曲',
    collection_type='uploaded_songs',
    query_filter={}
)

allocated_songs = Collection.objects.create(
    name='测试-分配歌曲',
    collection_type='allocated_songs',
    query_filter={'bid_type': 'song'}
)

# 2. 创建Phases
phase_upload = CompetitionPhase.objects.create(
    name='上传期',
    action_type='upload_song',
    output_collection=uploaded_songs,
    config={'max_uploads': 3}
)

phase_bid = CompetitionPhase.objects.create(
    name='竞标期',
    action_type='bid_song',
    input_collection=uploaded_songs,
    output_collection=uploaded_songs,
    config={'max_bids': 5}
)

phase_allocate = CompetitionPhase.objects.create(
    name='分配期',
    action_type='allocate_song',
    execution_type='system_execute',
    input_collection=uploaded_songs,
    output_collection=allocated_songs
)

phase_chart = CompetitionPhase.objects.create(
    name='制谱期',
    action_type='create_chart',
    input_collection=allocated_songs,
    require_in_input_collection=True,  # ← 关键测试点
    config={'required_files': ['maidata.txt']}
)

# 3. 测试用户权限
user_with_allocation = User.objects.get(username='user1')
user_without_allocation = User.objects.get(username='user2')

can1, msg1 = phase_chart.can_user_participate(user_with_allocation)
assert can1 == True

can2, msg2 = phase_chart.can_user_participate(user_without_allocation)
assert can2 == False
assert '不在参与者名单' in msg2

print('✅ 集成测试通过')
```

#### 步骤5.2：性能测试（1天）

```python
# 测试Collection查询性能

import time
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_collection_performance():
    # 创建大量测试数据
    songs = [Song.objects.create(title=f'Song {i}') for i in range(1000)]
    
    # 测试Collection查询
    collection = Collection.objects.create(
        collection_type='uploaded_songs',
        query_filter={'created_at__gte': '2026-02-01'}
    )
    
    start = time.time()
    qs = collection.get_queryset()
    count = qs.count()
    elapsed = time.time() - start
    
    print(f'查询1000条数据耗时: {elapsed:.3f}s')
    
    # 验证无N+1问题
    from django.db import connection
    query_count = len(connection.queries)
    assert query_count == 1  # 应该只有1次查询
    
    print('✅ 性能测试通过')
```

#### 步骤5.3：用户验收测试（1天）

- [ ] 管理员创建新比赛流程
- [ ] 用户正常上传歌曲
- [ ] 系统自动执行分配
- [ ] 未获得分配的用户无法制谱（权限限制生效）
- [ ] 前端配置动态拉取正常
- [ ] 后台管理界面正常

---

### 🚀 阶段6：部署上线（1天）

#### 步骤6.1：灰度发布（可选）

```python
# settings.py 添加功能开关
ENABLE_V25_ARCHITECTURE = os.getenv('ENABLE_V25', 'false').lower() == 'true'

# views.py 中使用
if settings.ENABLE_V25_ARCHITECTURE:
    config = phase.get_user_action_config(request.user)
else:
    # 使用旧逻辑
    config = get_legacy_config(phase)
```

```bash
# 环境变量控制
export ENABLE_V25=true
python manage.py runserver
```

#### 步骤6.2：正式部署

```bash
# 1. 备份生产数据库
pg_dump production_db > backup_before_v25.sql

# 2. 部署代码
git pull origin feature/v2.5-architecture
pip install -r requirements.txt

# 3. 执行迁移
python manage.py migrate songs

# 4. 重启服务
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# 5. 验证
python manage.py shell
>>> from songs.models import Collection, CompetitionPhase
>>> Collection.objects.count()
>>> CompetitionPhase.objects.first().phase_category
```

#### 步骤6.3：监控与回滚

```bash
# 监控日志
tail -f /var/log/gunicorn/error.log

# 如果出现问题，回滚
git revert <commit-hash>
python manage.py migrate songs <previous_migration>
sudo systemctl restart gunicorn
```

---

### 📊 验收标准

| 功能点 | 验收标准 | 负责人 |
|-------|---------|--------|
| Collection模型 | 可创建、查询、统计数量 | 后端 |
| Phase扩展字段 | 所有新字段正常工作 | 后端 |
| 权限检查 | require_in_input_collection生效 | 后端 |
| 配置拉取API | 前端能获取完整配置 | 后端+前端 |
| 管理后台 | 可视化管理Collection和Phase | 后端 |
| 前端动态配置 | 使用后台配置，无硬编码 | 前端 |
| 性能 | 无N+1查询，响应时间<100ms | 后端 |
| 兼容性 | 现有功能不受影响 | 全栈 |

---

### 🎯 里程碑时间表

| 周次 | 阶段 | 交付物 | 状态 |
|-----|------|--------|------|
| Week 1 | 准备+数据库迁移 | Collection模型、Phase扩展 | ⏳ |
| Week 2 | 后端API+测试 | 新API端点、PhaseExecutor | ⏳ |
| Week 3 | 管理后台+前端+部署 | Admin界面、前端适配、上线 | ⏳ |

---

### 🔧 工具和脚本

**快速创建Collection脚本**：

```python
# scripts/create_collections.py
from songs.models import Collection

def create_default_collections():
    """创建默认Collections"""
    collections = [
        {
            'name': '2026春季上传歌曲',
            'collection_type': 'uploaded_songs',
            'query_filter': {}
        },
        {
            'name': '2026春季分配歌曲',
            'collection_type': 'allocated_songs',
            'query_filter': {'bid_type': 'song'}
        },
        {
            'name': '2026春季谱面',
            'collection_type': 'submitted_charts',
            'query_filter': {'status': 'final_submitted'}
        },
    ]
    
    for data in collections:
        col, created = Collection.objects.get_or_create(
            name=data['name'],
            defaults=data
        )
        print(f'{"创建" if created else "已存在"}: {col.name}')

if __name__ == '__main__':
    create_default_collections()
```

**Phase配置检查脚本**：

```python
# scripts/check_phase_config.py
from songs.models import CompetitionPhase

def check_phases():
    """检查Phase配置完整性"""
    phases = CompetitionPhase.objects.all()
    
    for phase in phases:
        issues = []
        
        if not phase.phase_category:
            issues.append('缺少phase_category')
        
        if not phase.action_type:
            issues.append('缺少action_type')
        
        if phase.require_in_input_collection and not phase.input_collection:
            issues.append('要求input_collection但未设置')
        
        if issues:
            print(f'❌ {phase.name}: {", ".join(issues)}')
        else:
            print(f'✅ {phase.name}')

if __name__ == '__main__':
    check_phases()
```

---

### 📚 文档和培训

- [ ] 更新API文档（Swagger/OpenAPI）
- [ ] 编写管理员操作手册
- [ ] 录制视频教程（如何配置比赛流程）
- [ ] 为前端开发者提供配置拉取示例

---

**预计总耗时**: 2-3周  
**建议团队规模**: 1-2名后端 + 1名前端  
**风险等级**: 🟢 低（渐进式改造，可随时回滚）

---

## 优势总结（V2.5混合架构）

### ✅ 相比其他方案的对比

| 对比项 | v1.0 (纯Collection) | v2.0 (仅Phase增强) | **v2.5 (混合架构)** | 优势 |
|--------|-------------------|------------------|-------------------|------|
| **新增模型** | 4个 | 0个 | **1个（Collection轻量级）** | ✅ 改动适中 |
| **数据关系** | GenericForeignKey | 无 | **JSON查询条件** | ✅ 性能好 |
| **数据流清晰度** | 极高 | 低（隐式依赖） | **高（显式Collection）** | ✅ 易理解 |
| **类型安全** | 低（动态） | 高（固定10种）| **高（固定action_type）** | ✅ 防错误 |
| **参与限制** | 复杂实现 | 难实现 | **内置支持（require_in_input_collection）** | ✅ 开箱即用 |
| **后台配置** | 需自定义 | 基本支持 | **完整支持（get_user_action_config）** | ✅ 功能完善 |
| **重构成本** | 高 | 低 | **中** | ✅ 可接受 |

### ✅ V2.5核心优势

#### 1. **解决用户问题1：后台配置前端拉取**
```python
# 后台：在config中定义所有限制
phase.config = {
    'max_uploads': 3,
    'allowed_formats': ['mp3'],
    'max_file_size_mb': 10
}

# 前端：一个API拿到所有配置
const config = await api.get('/api/songs/phase/config/')
// → 前端无需硬编码任何限制，完全动态化
```

#### 2. **解决用户问题2：Collection-based参与限制**
```python
# 限制只有获得分配的用户才能制谱
phase_chart = Phase.objects.create(
    input_collection=allocated_songs,
    require_in_input_collection=True  # ← 自动检查用户是否在集合中
)

# 自动权限检查
can, msg = phase_chart.can_user_participate(user)
# → (False, "您不在参与者名单中")
```

#### 3. **兼顾类型安全和数据流清晰**
- **固定10种action_type**：防止拼写错误，IDE自动补全
- **轻量级Collection**：明确数据流向（uploaded_songs → allocated_songs → submitted_charts）
- **无GenericForeignKey**：避免N+1查询，使用JSON过滤条件

#### 4. **最小化改动，最大化收益**
- 新增1个Collection模型（100行代码）
- Phase模型增加3个字段（input_collection, output_collection, require_in_input_collection）
- 添加2个方法（can_user_participate, get_user_action_config）
- **无需修改现有Song/Chart/Bid等核心模型**

### ✅ 满足所有需求

| 需求 | v2.5实现方式 |
|------|-------------|
| ✅ 基于三种页面（songs/charts/eval） | `phase_category`（固定3种） |
| ✅ 可重排比赛结构 | `depends_on` + `order` |
| ✅ 区分用户操作和系统执行 | `execution_type` |
| ✅ 明确数据流向 | `input_collection` → `output_collection` |
| ✅ 参与者限制 | `require_in_input_collection` |
| ✅ 后台配置拉取 | `get_user_action_config()` |
| ✅ 重构代价小 | 仅1个新模型 + 3个Phase字段 |

### ✅ 核心设计思想

> **Collection不是数据表，是查询条件的容器**

```python
# Collection存储的是"如何查询数据"，而不是"数据本身"
collection = Collection.objects.create(
    collection_type='allocated_songs',  # 决定查询哪个模型
    query_filter={'status': 'allocated'}  # 过滤条件
)

# 运行时动态生成QuerySet
qs = collection.get_queryset()  
# → 等价于 BidResult.objects.filter(bid_type='song', status='allocated')
```

**优势**：
- 避免数据冗余（不存储actual数据）
- 避免关系复杂（无GenericForeignKey）
- 保持灵活性（query_filter可调整）
- 性能优化（直接QuerySet查询）

---

## 后续扩展

### 可选增强（未来）

如果后续需要更高的灵活性，可以考虑：

1. **多比赛支持**
   ```python
   class Competition(models.Model):
       name = models.CharField(max_length=200)
       is_active = models.BooleanField(default=True)
   
   # Phase 添加 competition 字段
   competition = models.ForeignKey(Competition, ...)
   ```

2. **阶段模板**
   ```python
   class PhaseTemplate(models.Model):
       """可复用的阶段模板"""
       name = models.CharField(max_length=100)
       phase_category = models.CharField(...)
       action_type = models.CharField(...)
       default_config = models.JSONField()
   
   # 快速创建阶段
   phase = PhaseTemplate.objects.get(name='标准竞标').create_instance(
       start_time='2026-02-01',
       end_time='2026-02-07'
   )
   ```

3. **可视化配置工具**
   - 拖拽式阶段编排
   - 自动验证依赖关系
   - 预览比赛流程图

---

## 总结

### 核心改进

> **轻量级Collection + Phase增强 = 灵活的比赛流程配置**

**新增内容**：
```python
# 1. Collection模型（约100行代码）
class Collection(models.Model):
    collection_type = CharField(choices=[...])  # 5种固定类型
    query_filter = JSONField()                   # 动态查询条件
    
    def get_queryset(self):                      # 返回QuerySet
    def contains_user(self, user):               # 权限检查

# 2. Phase模型新增字段
phase_category         # 固定3种：song/chart/review
execution_type         # 固定2种：user_action/system_execute  
action_type            # 固定10种操作类型
input_collection       # ForeignKey(Collection)
output_collection      # ForeignKey(Collection)
require_in_input_collection  # Boolean
depends_on             # ForeignKey(self)

# 3. Phase新增方法
def can_user_participate(self, user)      # 权限检查
def get_user_action_config(self, user)    # 配置拉取
```

### 数据存储位置

| 数据类型 | 存储位置 | 是否修改？ |
|---------|---------|-----------|
| 歌曲 | `songs_song`表 | ❌ 不变 |
| 谱面 | `songs_chart`表 | ❌ 不变 |
| 竞标 | `songs_bid`表 | ❌ 不变 |
| 分配结果 | `songs_bidresult`表 | ❌ 不变 |
| 互评 | `songs_peerreview`表 | ❌ 不变 |
| Collection | `songs_collection`表 | ✅ 新增（仅存查询条件） |

### 实施成本

| 阶段 | 耗时 | 风险 |
|------|------|------|
| 数据库迁移 | 3-5天 | 🟢 低 |
| 后端API实现 | 1周 | 🟢 低 |
| 管理界面 | 2-3天 | 🟢 低 |
| 前端适配 | 1-2天 | 🟡 中 |
| 测试部署 | 3天 | 🟢 低 |
| **总计** | **2-3周** | **🟢 低** |

### 关键决策依据

**为什么选择V2.5而非V1.0或V2.0？**

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **V1.0** | 极高灵活性 | 复杂度高、N+1问题 | 需要频繁改变数据结构的系统 |
| **V2.0** | 改动最小 | 数据流不清晰、参与限制难实现 | 临时快速方案 |
| **V2.5** ✅ | 平衡灵活性与复杂度 | 需要新增1个模型 | 本项目（推荐） |

---

## ❓ FAQ（常见问题）

### Q1: Collection会不会导致数据冗余？
**A**: 不会。Collection**不存储实际数据**，只存储查询条件（JSON）。歌曲、谱面数据仍在原表中。

### Q2: 如何保证Collection查询性能？
**A**: Collection调用`get_queryset()`时直接查询目标表（Song/Chart），无需JOIN，无N+1问题。

```python
# 实际执行的SQL（只有1次查询）
SELECT * FROM songs_chart WHERE status='final_submitted'
```

### Q3: 前端需要大改吗？
**A**: 几乎不需要。只需调用新的`/api/songs/phase/config/`端点获取配置，移除硬编码限制。

### Q4: 现有数据会丢失吗？
**A**: 不会。所有数据迁移都是**增量式**的（只添加字段），原有数据完全保留。

### Q5: 如果要回滚怎么办？
**A**: 可以安全回滚。新增字段都设置了`null=True`，删除字段不影响原有逻辑。

### Q6: Collection的5种类型够用吗？
**A**: 对于当前的比赛流程（上传→竞标→制谱→互评）完全够用。未来可通过修改CHOICES轻松扩展。

### Q7: 为什么不用GenericForeignKey？
**A**: GenericForeignKey会导致：
- 无法使用数据库外键约束
- 需要JOIN ContentType表
- 容易产生N+1查询问题

V2.5的配置驱动方式避免了这些问题。

### Q8: 多个比赛同时进行怎么办？
**A**: 当前方案支持通过Collection的`query_filter`区分不同比赛：
```python
collection = Collection.objects.create(
    query_filter={'created_at__gte': '2026-02-01', 'created_at__lt': '2026-05-01'}
)
```

未来可扩展Competition模型（见"后续扩展"章节）。

### Q9: 如何测试新架构？
**A**: 参考[实施路线图-阶段5](#-阶段5测试与验证3天)中的集成测试和性能测试脚本。

### Q10: 文档有示例代码吗？
**A**: 有！见以下章节：
- [Collection使用示例](#-collection--phase-完整示例解决用户提出的两个问题)
- [前端动态配置](#前端适配完全动态化后台配置驱动)
- [实施脚本](#工具和脚本)

---

## 📚 快速参考

### Collection类型速查

| collection_type | 查询模型 | 常用query_filter |
|----------------|----------|------------------|
| `uploaded_songs` | Song | `{}` 或 `{"created_at__gte": "2026-02-01"}` |
| `allocated_songs` | BidResult | `{"bid_type": "song"}` |
| `submitted_charts` | Chart | `{"status": "final_submitted"}` |
| `allocated_charts` | BidResult | `{"bid_type": "chart"}` |
| `peer_reviews` | PeerReview | `{"created_at__gte": "2026-03-01"}` |

### Action Type速查

| action_type | phase_category | execution_type | 说明 |
|-------------|----------------|----------------|------|
| `upload_song` | song | user_action | 用户上传歌曲 |
| `bid_song` | song | user_action | 用户竞标歌曲 |
| `allocate_song` | song | system_execute | 系统分配歌曲 |
| `create_chart` | chart | user_action | 用户制作谱面 |
| `bid_chart` | chart | user_action | 用户竞标谱面 |
| `allocate_chart` | chart | system_execute | 系统分配谱面 |
| `peer_review` | review | user_action | 用户互评 |
| `allocate_review` | review | system_execute | 系统分配评分任务 |
| `judge_review` | review | user_action | 评委评分 |
| `voting` | review | user_action | 用户投票 |

### 常用配置字段

```python
# Phase.config示例
{
    # 上传歌曲
    "max_uploads": 3,
    "allowed_formats": ["mp3", "wav"],
    "max_file_size_mb": 10,
    
    # 竞标
    "max_bids": 5,
    "random_cost": 200,
    "allow_self_bidding": True,
    
    # 制谱
    "is_partial": False,
    "required_files": ["maidata.txt", "audio.mp3"],
    
    # 互评
    "reviews_per_user": 8,
    "max_score": 50
}
```

### 核心API端点

| 端点 | 方法 | 用途 | 返回 |
|------|------|------|------|
| `/api/songs/phase/config/` | GET | 获取当前阶段配置 | 包含所有后台配置的JSON |
| `/api/songs/phase/info/` | GET | 获取用户操作信息 | 包含用户数据的JSON |
| `/api/songs/status/` | GET | 获取比赛状态（兼容） | 兼容旧版的状态信息 |

---

## 📞 支持与联系

- **技术支持**: GitHub Issues
- **文档更新**: 随代码提交同步更新
- **紧急联系**: [填写团队联系方式]

---

**文档版本**: V2.5（混合架构）  
**最后更新**: 2026-02-10  
**维护者**: GitHub Copilot  
**License**: MIT
