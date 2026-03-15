"""
互评评分汇总独立导出脚本

用法：
    python export_peer_reviews.py                    # 导出全部轮次
    python export_peer_reviews.py 1                  # 导出轮次 ID=1
    python export_peer_reviews.py 1 my_output.xlsx   # 自定义输出文件名
"""

import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from songs.exports import export_peer_review_scores  # noqa: E402  (django must be set up first)
from songs.models import BiddingRound  # noqa: E402


def main():
    bidding_round_id = None
    output_path = None

    args = sys.argv[1:]
    if args:
        try:
            bidding_round_id = int(args[0])
        except ValueError:
            print(f'[ERROR] 无效的轮次 ID：{args[0]}，应为整数')
            sys.exit(1)

    if len(args) >= 2:
        output_path = args[1]

    if output_path is None:
        if bidding_round_id is not None:
            try:
                round_name = BiddingRound.objects.get(id=bidding_round_id).name
            except BiddingRound.DoesNotExist:
                print(f'[ERROR] 竞标轮次 {bidding_round_id} 不存在')
                sys.exit(1)
            safe_name = round_name.replace('/', '_').replace(' ', '_')
            output_path = f'peer_review_scores_round{bidding_round_id}_{safe_name}.xlsx'
        else:
            output_path = 'peer_review_scores_all.xlsx'

    print(f'导出中... 轮次ID={bidding_round_id or "全部"}')

    xlsx_bytes = export_peer_review_scores(bidding_round_id=bidding_round_id)

    with open(output_path, 'wb') as f:
        f.write(xlsx_bytes)

    print(f'[OK] 已生成：{output_path}')


if __name__ == '__main__':
    main()
