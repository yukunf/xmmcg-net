"""
互评任务分配逻辑单元测试
测试 PeerReviewService.allocate_peer_reviews 的核心正确性
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from songs.models import BiddingRound, Song, Chart, PeerReviewAllocation
from songs.bidding_service import PeerReviewService

User = get_user_model()


def make_user(username):
    return User.objects.create_user(username=username, password='test')


def make_round(name='test_round'):
    return BiddingRound.objects.create(name=name, bidding_type='chart', status='completed')


_song_counter = 0

def make_song(user, title='song'):
    global _song_counter
    _song_counter += 1
    return Song.objects.create(
        user=user,
        title=title,
        audio_file='',
        audio_hash=f'deadbeef{_song_counter:056x}',
        file_size=0,
    )


def make_chart(user, bidding_round, song, status='final_submitted', part_one_chart=None):
    return Chart.objects.create(
        user=user,
        bidding_round=bidding_round,
        song=song,
        status=status,
        part_one_chart=part_one_chart,
        is_part_one=(part_one_chart is None),
    )


class TestAllocateBasic(TestCase):
    """基本场景：N 个用户各提交 1 张谱面"""

    def setUp(self):
        self.round = make_round()
        self.users = [make_user(f'u{i}') for i in range(5)]
        self.charts = [
            make_chart(u, self.round, make_song(u, f'song{i}'))
            for i, u in enumerate(self.users)
        ]

    def _run(self, min_reviews=3):
        return PeerReviewService.allocate_peer_reviews(self.round.id, min_reviews)

    def test_each_chart_reaches_target(self):
        self._run(min_reviews=3)
        for chart in self.charts:
            count = PeerReviewAllocation.objects.filter(chart=chart).count()
            self.assertEqual(count, 3, f'Chart {chart.id} 应有 3 个评分，实际 {count}')

    def test_no_self_review(self):
        self._run(min_reviews=3)
        for alloc in PeerReviewAllocation.objects.select_related('reviewer', 'chart__user'):
            self.assertNotEqual(
                alloc.reviewer_id, alloc.chart.user_id,
                f'{alloc.reviewer.username} 评了自己的谱面 chart={alloc.chart_id}'
            )

    def test_no_duplicate_assignments(self):
        self._run(min_reviews=3)
        allocs = PeerReviewAllocation.objects.all()
        pairs = [(a.reviewer_id, a.chart_id) for a in allocs]
        self.assertEqual(len(pairs), len(set(pairs)), '存在重复分配')

    def test_reached_target_flag(self):
        result = self._run(min_reviews=3)
        self.assertTrue(result['reached_target'])

    def test_reallocation_clears_previous(self):
        self._run(min_reviews=2)
        count_first = PeerReviewAllocation.objects.count()
        self._run(min_reviews=2)
        count_second = PeerReviewAllocation.objects.count()
        self.assertEqual(count_first, count_second, '重新分配后总数应相同（旧分配被清除）')

    def test_invalid_min_raises(self):
        with self.assertRaises(ValidationError):
            PeerReviewService.allocate_peer_reviews(self.round.id, 0)


class TestAllocateBalance(TestCase):
    """分配均衡性：每张谱面评分数尽量均等"""

    def test_perfectly_divisible(self):
        """4 人 4 谱，每张目标 3 个评分 → 每人恰好 3 个任务"""
        r = make_round()
        users = [make_user(f'bal{i}') for i in range(4)]
        for i, u in enumerate(users):
            make_chart(u, r, make_song(u, f's{i}'))

        result = PeerReviewService.allocate_peer_reviews(r.id, min_reviews_per_chart=3)
        self.assertEqual(result['reviews_per_chart_min'], 3)
        self.assertEqual(result['reviews_per_chart_max'], 3)
        self.assertTrue(result['reached_target'])

    def test_uneven_tasks_per_reviewer(self):
        """5 人 5 谱，目标每张 4 评分，总 20 次，每人最多评 4 张（不评自己的）
           20 / 5 = 4，每人恰好 4 个任务"""
        r = make_round()
        users = [make_user(f'even{i}') for i in range(5)]
        for i, u in enumerate(users):
            make_chart(u, r, make_song(u, f's{i}'))

        result = PeerReviewService.allocate_peer_reviews(r.id, min_reviews_per_chart=4)
        self.assertEqual(result['reviews_per_chart_min'], 4)
        self.assertTrue(result['reached_target'])


class TestAllocateTwoPartChart(TestCase):
    """两部分谱面场景：每张完成稿有 2 个贡献者 → 评分者数 > 谱面数"""

    def setUp(self):
        """
        构造 3 张两部分完成稿谱面：
          - part1 作者：p1_0, p1_1, p1_2
          - part2 作者（提交完成稿）：p2_0, p2_1, p2_2
          共 6 个评分者，3 张谱面
        """
        self.round = make_round()
        self.p1_users = [make_user(f'p1_{i}') for i in range(3)]
        self.p2_users = [make_user(f'p2_{i}') for i in range(3)]
        self.charts = []
        for i in range(3):
            song = make_song(self.p1_users[i], f'song{i}')
            part1 = make_chart(self.p1_users[i], self.round, song, status='part_submitted')
            part2 = make_chart(self.p2_users[i], self.round, song,
                               status='final_submitted', part_one_chart=part1)
            self.charts.append(part2)

    def test_both_contributors_excluded(self):
        """part1 和 part2 作者都不能评自己参与的谱面"""
        PeerReviewService.allocate_peer_reviews(self.round.id, min_reviews_per_chart=2)
        for alloc in PeerReviewAllocation.objects.select_related('chart__user', 'chart__part_one_chart__user'):
            chart = alloc.chart
            contributors = {chart.user_id}
            if chart.part_one_chart:
                contributors.add(chart.part_one_chart.user_id)
            self.assertNotIn(
                alloc.reviewer_id, contributors,
                f'reviewer {alloc.reviewer_id} 是 chart {chart.id} 的贡献者，不应被分配'
            )

    def test_each_chart_gets_target_reviews(self):
        """即使评分者是谱面数的 2 倍，每张谱面仍能达到目标"""
        result = PeerReviewService.allocate_peer_reviews(self.round.id, min_reviews_per_chart=2)
        self.assertEqual(result['reviews_per_chart_min'], 2)
        self.assertTrue(result['reached_target'])

    def test_no_duplicates(self):
        PeerReviewService.allocate_peer_reviews(self.round.id, min_reviews_per_chart=2)
        allocs = PeerReviewAllocation.objects.all()
        pairs = [(a.reviewer_id, a.chart_id) for a in allocs]
        self.assertEqual(len(pairs), len(set(pairs)))


class TestAllocateMostConstrainedFirst(TestCase):
    """
    验证"最受限优先"修复：
    Chart A 只有 1 个合法评分者 X
    Chart B 有 X 和 Y 两个合法评分者
    若先处理 B 并把 X 分给 B，则 A 永远得不到评分。
    正确行为：X 应先分配给 A。
    """

    def setUp(self):
        """
        3 个用户：X, Y, Z
        Chart A 作者 Z（贡献者={Z}，合法评分者={X, Y}）
        Chart B 作者 X、Y（两部分，贡献者={X,Y}，合法评分者={Z}）
        目标每张谱 1 个评分，total_target = 2
        """
        self.round = make_round()
        self.x = make_user('x_user')
        self.y = make_user('y_user')
        self.z = make_user('z_user')

        song_a = make_song(self.z, 'song_a')
        song_b = make_song(self.x, 'song_b')

        # Chart A：只有 Z 一个贡献者，X 和 Y 均可评
        self.chart_a = make_chart(self.z, self.round, song_a)

        # Chart B：X 是 part1 作者，Y 是 part2 作者（完成稿），两人都不能评
        part1_b = make_chart(self.x, self.round, song_b, status='part_submitted')
        self.chart_b = make_chart(self.y, self.round, song_b,
                                  status='final_submitted', part_one_chart=part1_b)

    def test_both_charts_get_one_review(self):
        """两张谱面都应获得 1 个评分"""
        result = PeerReviewService.allocate_peer_reviews(self.round.id, min_reviews_per_chart=1)
        count_a = PeerReviewAllocation.objects.filter(chart=self.chart_a).count()
        count_b = PeerReviewAllocation.objects.filter(chart=self.chart_b).count()
        self.assertEqual(count_a, 1, f'Chart A 应得 1 个评分，实际 {count_a}')
        self.assertEqual(count_b, 1, f'Chart B 应得 1 个评分，实际 {count_b}')
        self.assertTrue(result['reached_target'])

    def test_chart_b_reviewer_is_z(self):
        """Chart B 唯一的合法评分者是 Z"""
        PeerReviewService.allocate_peer_reviews(self.round.id, min_reviews_per_chart=1)
        alloc_b = PeerReviewAllocation.objects.get(chart=self.chart_b)
        self.assertEqual(alloc_b.reviewer_id, self.z.id,
                         'Chart B 的评分者应是 Z（唯一合法评分者）')


class TestAllocatePartialFallback(TestCase):
    """
    评分者不够的降级场景：
    2 个用户各提交 1 张谱面，目标每张 2 个评分，
    但每人只能评对方 1 张（各只有 1 个合法评分者），
    实际每张只能得 1 个评分。
    """

    def setUp(self):
        self.round = make_round()
        u0 = make_user('part_u0')
        u1 = make_user('part_u1')
        self.c0 = make_chart(u0, self.round, make_song(u0, 's0'))
        self.c1 = make_chart(u1, self.round, make_song(u1, 's1'))

    def test_partial_allocation_does_not_raise(self):
        """目标无法达到时，不应抛异常，应静默降级"""
        result = PeerReviewService.allocate_peer_reviews(self.round.id, min_reviews_per_chart=2)
        self.assertFalse(result['reached_target'])
        self.assertEqual(result['reviews_per_chart_min'], 1)

    def test_still_no_self_review(self):
        PeerReviewService.allocate_peer_reviews(self.round.id, min_reviews_per_chart=2)
        for alloc in PeerReviewAllocation.objects.select_related('chart__user'):
            self.assertNotEqual(alloc.reviewer_id, alloc.chart.user_id)

    def test_no_duplicates(self):
        PeerReviewService.allocate_peer_reviews(self.round.id, min_reviews_per_chart=2)
        allocs = PeerReviewAllocation.objects.all()
        pairs = [(a.reviewer_id, a.chart_id) for a in allocs]
        self.assertEqual(len(pairs), len(set(pairs)))
