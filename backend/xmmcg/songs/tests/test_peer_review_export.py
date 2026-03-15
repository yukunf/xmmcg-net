"""
互评评分汇总导出功能单元测试

测试 songs.exports.export_peer_review_scores 的正确性：
  - 只导出 final_submitted 谱面
  - 列以评分人用户名标注
  - 「评分」表：纯分数，每人一列
  - 「评分与评语」表：每人两列（分数 + 评语相邻）
  - 真爱票数统计
  - 竞标轮次过滤
"""

import io

from django.test import TestCase
from openpyxl import load_workbook

from songs.exports import export_peer_review_scores
from songs.models import PeerReview
from songs.tests.test_peer_review_allocation import (
    make_chart,
    make_round,
    make_song,
    make_user,
)


def make_review(reviewer, chart, score, comment='', favorite=False):
    return PeerReview.objects.create(
        reviewer=reviewer,
        chart=chart,
        score=score,
        comment=comment,
        favorite=favorite,
    )


def parse_wb(xlsx_bytes):
    return load_workbook(io.BytesIO(xlsx_bytes))


def ws1(xlsx_bytes):
    return parse_wb(xlsx_bytes)['评分']


def ws2(xlsx_bytes):
    return parse_wb(xlsx_bytes)['评分与评语']


# ---------------------------------------------------------------------------
# 空数据 / 无完稿谱面
# ---------------------------------------------------------------------------

class TestExportEmpty(TestCase):

    def test_both_sheets_exist(self):
        wb = parse_wb(export_peer_review_scores())
        self.assertIn('评分', wb.sheetnames)
        self.assertIn('评分与评语', wb.sheetnames)

    def test_scores_sheet_header_only(self):
        # 无谱面：标题行 + 列头行 = 2 行，无数据行
        ws = ws1(export_peer_review_scores())
        # 行1 = 标题，行2 = 列头（谱面ID/歌曲名/谱师名/真爱票数），无行3
        self.assertIsNone(ws.cell(3, 1).value)
        self.assertEqual(ws.cell(2, 1).value, '谱面ID')
        self.assertEqual(ws.cell(2, 2).value, '歌曲名')
        self.assertEqual(ws.cell(2, 3).value, '谱师名')
        self.assertEqual(ws.cell(2, 4).value, '真爱票数')

    def test_part_submitted_excluded(self):
        r = make_round()
        u = make_user('drafter')
        s = make_song(u, 'draft_song')
        c = make_chart(u, r, s, status='part_submitted')
        make_review(u, c, 30)

        ws = ws1(export_peer_review_scores())
        self.assertIsNone(ws.cell(3, 1).value)  # part_submitted 不导出

    def test_under_review_included(self):
        r = make_round()
        u1 = make_user('ur_u1')
        u2 = make_user('ur_u2')
        s = make_song(u1, 'ur_song')
        c = make_chart(u1, r, s, status='under_review')
        make_review(u2, c, 40)

        ws = ws1(export_peer_review_scores())
        self.assertIsNotNone(ws.cell(3, 1).value)  # under_review 应被导出


# ---------------------------------------------------------------------------
# 单张完稿谱面，3 位评分人
# ---------------------------------------------------------------------------

class TestExportSingleChart(TestCase):

    def setUp(self):
        self.round = make_round()
        self.designer = make_user('adesigner')
        # 用户名按字典序：rv_alice < rv_bob < rv_carol
        self.rv_alice = make_user('rv_alice')
        self.rv_bob   = make_user('rv_bob')
        self.rv_carol = make_user('rv_carol')
        self.song  = make_song(self.designer, 'MySong')
        self.chart = make_chart(self.designer, self.round, self.song, status='final_submitted')
        self.chart.designer = 'DesignerAlias'
        self.chart.save()

        make_review(self.rv_alice, self.chart, 40, 'nice',      favorite=True)
        make_review(self.rv_bob,   self.chart, 35, 'ok')
        make_review(self.rv_carol, self.chart, 45, 'excellent', favorite=True)

    # --- 评分表 ---

    def test_scores_sheet_column_headers(self):
        ws = ws1(export_peer_review_scores())
        # 行2：谱面ID | 歌曲名 | 谱师名 | rv_alice | rv_bob | rv_carol | 真爱票数
        self.assertEqual(ws.cell(2, 4).value, 'rv_alice')
        self.assertEqual(ws.cell(2, 5).value, 'rv_bob')
        self.assertEqual(ws.cell(2, 6).value, 'rv_carol')
        self.assertEqual(ws.cell(2, 7).value, '真爱票数')

    def test_scores_sheet_data(self):
        ws = ws1(export_peer_review_scores())
        row = [ws.cell(3, c).value for c in range(1, 8)]
        self.assertEqual(row[0], self.chart.id)
        self.assertEqual(row[1], 'MySong')
        self.assertEqual(row[2], 'DesignerAlias')
        self.assertEqual(row[3], 40)   # rv_alice
        self.assertEqual(row[4], 35)   # rv_bob
        self.assertEqual(row[5], 45)   # rv_carol
        self.assertEqual(row[6], 2)    # 真爱票数

    # --- 评分与评语表 ---

    def test_comments_sheet_reviewer_header_row(self):
        ws = ws2(export_peer_review_scores())
        # 行2：谱面ID | 歌曲名 | 谱师名 | rv_alice(merge2) | rv_bob(merge2) | rv_carol(merge2) | 真爱票数
        self.assertEqual(ws.cell(2, 4).value, 'rv_alice')
        self.assertEqual(ws.cell(2, 6).value, 'rv_bob')
        self.assertEqual(ws.cell(2, 8).value, 'rv_carol')

    def test_comments_sheet_subheader_row(self):
        ws = ws2(export_peer_review_scores())
        # 行3：... | 评分 | 评语 | 评分 | 评语 | 评分 | 评语 | (空)
        self.assertEqual(ws.cell(3, 4).value, '评分')
        self.assertEqual(ws.cell(3, 5).value, '评语')
        self.assertEqual(ws.cell(3, 6).value, '评分')
        self.assertEqual(ws.cell(3, 7).value, '评语')

    def test_comments_sheet_data(self):
        ws = ws2(export_peer_review_scores())
        # 行4：数据
        row = [ws.cell(4, c).value for c in range(1, 12)]
        self.assertEqual(row[0], self.chart.id)
        self.assertEqual(row[1], 'MySong')
        self.assertEqual(row[2], 'DesignerAlias')
        # rv_alice: col4=评分, col5=评语
        self.assertEqual(row[3], 40)
        self.assertEqual(row[4], 'nice')
        # rv_bob: col6, col7
        self.assertEqual(row[5], 35)
        self.assertEqual(row[6], 'ok')
        # rv_carol: col8, col9
        self.assertEqual(row[7], 45)
        self.assertEqual(row[8], 'excellent')
        # 真爱票数: col10
        self.assertEqual(row[9], 2)

    # --- 轮次过滤 ---

    def test_round_filter_match(self):
        ws = ws1(export_peer_review_scores(bidding_round_id=self.round.id))
        self.assertIsNotNone(ws.cell(3, 1).value)

    def test_round_filter_no_match(self):
        ws = ws1(export_peer_review_scores(bidding_round_id=self.round.id + 999))
        self.assertIsNone(ws.cell(3, 1).value)


# ---------------------------------------------------------------------------
# 多张谱面，评分人不完全重叠
# ---------------------------------------------------------------------------

class TestExportMultipleCharts(TestCase):

    def setUp(self):
        self.round = make_round()
        self.u1 = make_user('zz_u1')
        self.u2 = make_user('aa_u2')   # 字典序最小
        self.u3 = make_user('mm_u3')

        s1 = make_song(self.u1, 'song1')
        s2 = make_song(self.u2, 'song2')
        self.c1 = make_chart(self.u1, self.round, s1, status='final_submitted')
        self.c2 = make_chart(self.u2, self.round, s2, status='final_submitted')

        # c1: u2 和 u3 评分；c2: u1、u2、u3 都评分 → 3 位评分人
        make_review(self.u2, self.c1, 30, 'c1u2')
        make_review(self.u3, self.c1, 25, 'c1u3')
        make_review(self.u1, self.c2, 40, 'c2u1')
        make_review(self.u2, self.c2, 38, 'c2u2')
        make_review(self.u3, self.c2, 42, 'c2u3')

    def test_reviewer_columns_sorted_by_username(self):
        ws = ws1(export_peer_review_scores())
        # 字典序：aa_u2 < mm_u3 < zz_u1
        self.assertEqual(ws.cell(2, 4).value, 'aa_u2')
        self.assertEqual(ws.cell(2, 5).value, 'mm_u3')
        self.assertEqual(ws.cell(2, 6).value, 'zz_u1')

    def test_missing_reviewer_is_none(self):
        ws = ws1(export_peer_review_scores())
        # c1 没有 zz_u1 的评分，第7列（col6 for zz_u1 → index 3+2=6）应为 None
        # c1 是第一张谱面（row3），zz_u1 在第6列
        self.assertIsNone(ws.cell(3, 6).value)

    def test_two_data_rows(self):
        ws = ws1(export_peer_review_scores())
        self.assertIsNotNone(ws.cell(3, 1).value)
        self.assertIsNotNone(ws.cell(4, 1).value)
        self.assertIsNone(ws.cell(5, 1).value)

    def test_bidding_round_ids_multi(self):
        round2 = make_round('round2')
        u4 = make_user('xx_u4')
        s3 = make_song(u4, 'song3')
        c3 = make_chart(u4, round2, s3, status='final_submitted')
        make_review(self.u1, c3, 48, 'cross')

        ws = ws1(export_peer_review_scores(bidding_round_ids=[self.round.id, round2.id]))
        # 3 张谱面 → 行3、4、5 均有数据
        self.assertIsNotNone(ws.cell(5, 1).value)
        self.assertIsNone(ws.cell(6, 1).value)

    def test_bidding_round_ids_excludes_other_rounds(self):
        round2 = make_round('round2')
        u4 = make_user('xx_u4b')
        s3 = make_song(u4, 'song3b')
        c3 = make_chart(u4, round2, s3, status='final_submitted')
        make_review(self.u1, c3, 48, 'cross')

        ws = ws1(export_peer_review_scores(bidding_round_ids=[self.round.id]))
        self.assertIsNone(ws.cell(5, 1).value)  # round2 的谱面未被导出


# ---------------------------------------------------------------------------
# 真爱票统计
# ---------------------------------------------------------------------------

class TestExportFavoriteCount(TestCase):

    def test_favorite_count_correct(self):
        r = make_round()
        u1 = make_user('fav_u1')
        u2 = make_user('fav_u2')
        u3 = make_user('fav_u3')
        s = make_song(u1, 'fav_song')
        c = make_chart(u1, r, s, status='final_submitted')

        make_review(u2, c, 45, favorite=True)
        make_review(u3, c, 40, favorite=False)
        make_review(u1, c, 50, favorite=True)

        ws = ws1(export_peer_review_scores())
        fav_col = 3 + 3 + 1   # 3 meta + 3 reviewers + 1 fav = col 7
        self.assertEqual(ws.cell(3, fav_col).value, 2)

    def test_no_favorites(self):
        r = make_round()
        u1 = make_user('nf_u1')
        u2 = make_user('nf_u2')
        s = make_song(u1, 'nf_song')
        c = make_chart(u1, r, s, status='final_submitted')
        make_review(u2, c, 30, favorite=False)

        ws = ws1(export_peer_review_scores())
        fav_col = 3 + 1 + 1   # 3 meta + 1 reviewer + 1 fav = col 5
        self.assertEqual(ws.cell(3, fav_col).value, 0)
