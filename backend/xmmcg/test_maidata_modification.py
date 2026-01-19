"""
测试 maidata.txt 半成品标题修改功能
验证 _modify_maidata_for_part_chart 方法
"""

import os
import sys
import django

# 设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from songs.majdata_service import MajdataService


def test_modify_maidata():
    """测试标题修改功能"""
    
    print("=" * 60)
    print("测试 maidata.txt 半成品标题修改")
    print("=" * 60)
    
    # 测试用例1：普通标题
    print("\n测试用例 1: 普通标题")
    original1 = """&title=14平米にスーベニア
&artist=ChouCho
&des=Test Designer
&lv_1=1

# 谱面数据
E1,
"""
    
    modified1 = MajdataService._modify_maidata_for_part_chart(original1)
    
    print("原始内容:")
    print(original1[:100] + "...")
    print("\n修改后:")
    print(modified1[:100] + "...")
    
    if '&title=[谱面碎片]14平米にスーベニア' in modified1:
        print("✅ 测试通过：标题已正确添加 [谱面碎片] 标记")
    else:
        print("❌ 测试失败：标题未正确修改")
        print("预期: &title=[谱面碎片]14平米にスーベニア")
        for line in modified1.split('\n'):
            if line.startswith('&title='):
                print(f"实际: {line}")
    
    # 测试用例2：已有标记的标题（避免重复添加）
    print("\n" + "=" * 60)
    print("测试用例 2: 已有 [谱面碎片] 标记的标题")
    original2 = """&title=[谱面碎片]14平米にスーベニア
&artist=ChouCho
&des=Test Designer
"""
    
    modified2 = MajdataService._modify_maidata_for_part_chart(original2)
    
    print("原始内容:")
    print(original2[:80])
    print("\n修改后:")
    print(modified2[:80])
    
    if modified2.count('[谱面碎片]') == 1:
        print("✅ 测试通过：未重复添加标记")
    else:
        print("❌ 测试失败：重复添加了标记")
    
    # 测试用例3：日文标题
    print("\n" + "=" * 60)
    print("测试用例 3: 日文标题")
    original3 = """&title=セツナトリップ
&artist=Last Note.
&des=谱师名字
&lv_1=3
"""
    
    modified3 = MajdataService._modify_maidata_for_part_chart(original3)
    
    if '&title=[谱面碎片]セツナトリップ' in modified3:
        print("✅ 测试通过：日文标题正确修改")
    else:
        print("❌ 测试失败：日文标题未正确修改")
    
    # 测试用例4：中文标题
    print("\n" + "=" * 60)
    print("测试用例 4: 中文标题")
    original4 = """&title=夏日海风
&artist=测试歌手
&des=设计师
"""
    
    modified4 = MajdataService._modify_maidata_for_part_chart(original4)
    
    if '&title=[谱面碎片]夏日海风' in modified4:
        print("✅ 测试通过：中文标题正确修改")
    else:
        print("❌ 测试失败：中文标题未正确修改")
    
    # 测试用例5：空内容
    print("\n" + "=" * 60)
    print("测试用例 5: 空内容")
    original5 = ""
    
    modified5 = MajdataService._modify_maidata_for_part_chart(original5)
    
    if modified5 == "":
        print("✅ 测试通过：空内容处理正确")
    else:
        print("❌ 测试失败：空内容处理错误")
    
    # 测试用例6：多行复杂内容
    print("\n" + "=" * 60)
    print("测试用例 6: 完整的 maidata 文件")
    original6 = """&title=Test Song
&artist=Test Artist
&des=Test Designer
&lv_1=1
&lv_2=3
&lv_3=5
&lv_4=7+

# Basic
(120)
{4}
1,
2,
3,
4,

# Advanced
(150)
{8}
1-2[4:1],
3/4[8:1],
"""
    
    modified6 = MajdataService._modify_maidata_for_part_chart(original6)
    
    title_found = False
    for line in modified6.split('\n'):
        if line.startswith('&title='):
            if line == '&title=[谱面碎片]Test Song':
                print("✅ 测试通过：完整文件标题正确修改")
                title_found = True
            else:
                print(f"❌ 测试失败：标题为 {line}")
            break
    
    if not title_found:
        print("❌ 测试失败：未找到标题行")
    
    # 验证其他内容未被修改
    if '&artist=Test Artist' in modified6 and '&des=Test Designer' in modified6:
        print("✅ 测试通过：其他内容保持不变")
    else:
        print("❌ 测试失败：其他内容被意外修改")
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    test_modify_maidata()
