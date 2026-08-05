"""
测试 PPStructureV3 with 新 PaddlePaddle
"""
import sys, os, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz

# 先检查版本
import paddle
import paddleocr
print(f"PaddlePaddle: {paddle.__version__}")
print(f"PaddleOCR: {paddleocr.__version__}")

# 测试 PPStructureV3
from paddleocr import PPStructureV3

print("\n=== 初始化 PPStructureV3 ===")
try:
    pp = PPStructureV3(use_table_recognition=True)
    print("初始化成功!")
except Exception as e:
    print(f"初始化失败: {e}")
    print("尝试默认初始化...")
    pp = PPStructureV3()
    print("默认初始化成功!")

# 测试磁稳PDF第7页
pdf_path = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\磁稳产品手册(2025版).pdf'
doc = fitz.open(pdf_path)
page_num = 6
page = doc.load_page(page_num)
dpi = 300
pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
temp_path = "test_page.png"
pix.save(temp_path)
print(f"\n测试: {os.path.basename(pdf_path)} 第7页")

# 调用
print("\n=== 调用 predict ===")
result = pp.predict(temp_path)
print(f"返回类型: {type(result)}, 长度: {len(result)}")

for i, item in enumerate(result):
    if isinstance(item, dict):
        item_type = item.get('type', item.get('layout_type', 'unknown'))
        bbox = item.get('bbox', [])
        print(f"\n  [{i}] type={item_type}, bbox={bbox}")
        
        # 检查表格
        if 'table' in str(item_type).lower() or 'table' in str(item).lower():
            print(f"    *** 表格! ***")
        
        # 显示所有键
        for key in item.keys():
            val = item[key]
            if isinstance(val, str) and len(val) > 20:
                print(f"    {key}: str({len(val)})")
                if 'table' in str(item_type).lower() or key == 'html':
                    print(f"      前300字符: {val[:300]}")
            elif isinstance(val, list):
                print(f"    {key}: list({len(val)})")
                if len(val) > 0 and 'table' in str(item_type).lower():
                    if isinstance(val[0], dict):
                        print(f"      [0] keys: {list(val[0].keys())}")
                    elif isinstance(val[0], list):
                        print(f"      [0] list len: {len(val[0])}")
            elif isinstance(val, (int, float)):
                print(f"    {key}: {val}")

os.remove(temp_path)
doc.close()
