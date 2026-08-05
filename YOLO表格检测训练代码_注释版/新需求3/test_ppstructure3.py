"""
测试 PPStructure 类
"""
import sys, os, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from paddleocr import PPStructure

print("=== 初始化 PPStructure ===")
pp = PPStructure(table=True, ocr=True, show_log=False)
print("初始化成功")

# 测试磁稳PDF第7页
pdf_path = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\磁稳产品手册(2025版).pdf'
doc = fitz.open(pdf_path)
page_num = 6  # 第7页
page = doc.load_page(page_num)

# 渲染页面
dpi = 300
pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
temp_path = "test_page.png"
pix.save(temp_path)
print(f"页面渲染: {pix.width}x{pix.height}")

# PPStructure 识别
print("\n=== PPStructure 识别 ===")
result = pp(temp_path)

print(f"返回类型: {type(result)}")
if result:
    print(f"返回长度: {len(result)}")
    for i, item in enumerate(result):
        print(f"\n--- 结果项 {i} ---")
        if isinstance(item, dict):
            print(f"类型: dict")
            print(f"键: {list(item.keys())}")
            # 打印每个键值的摘要
            for key, val in item.items():
                if isinstance(val, str):
                    print(f"  {key}: str, len={len(val)}")
                    if len(val) < 200:
                        print(f"    内容: {val}")
                    else:
                        print(f"    前200字符: {val[:200]}")
                elif isinstance(val, list):
                    print(f"  {key}: list, len={len(val)}")
                    if len(val) > 0:
                        elem = val[0]
                        if isinstance(elem, (list, tuple)):
                            print(f"    第一个元素 (list): {elem[:3]}...")
                        elif isinstance(elem, dict):
                            print(f"    第一个元素 (dict): keys={list(elem.keys())[:5]}")
                        else:
                            print(f"    第一个元素: {type(elem).__name__} = {elem}")
                elif isinstance(val, int):
                    print(f"  {key}: int = {val}")
                elif isinstance(val, float):
                    print(f"  {key}: float = {val}")
                else:
                    print(f"  {key}: {type(val).__name__}")
        else:
            print(f"类型: {type(item).__name__}")
            print(f"值: {str(item)[:200]}")

os.remove(temp_path)
doc.close()
