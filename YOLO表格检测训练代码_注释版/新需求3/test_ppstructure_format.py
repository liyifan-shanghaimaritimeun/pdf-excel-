"""
测试 PPStructure(table=True) 输出格式
"""
import sys, os, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from paddleocr import PaddleOCR

# 初始化带table的OCR引擎
print("初始化 PPStructure(table=True)...")
ocr = PaddleOCR(
    lang='ch',
    use_angle_cls=True,
    show_log=False,
    table=True
)
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

# PPStructure识别
print("PPStructure 识别中...")
result = ocr.ocr(temp_path, cls=True)

if not result or not result[0]:
    print("返回空结果!")
else:
    print(f"识别到 {len(result[0])} 个结果项")
    
    # 探测输出格式
    for i, item in enumerate(result[0][:3]):
        print(f"\n--- 结果项 {i} ---")
        if isinstance(item, dict):
            print(f"类型: dict, 键: {list(item.keys())}")
            for key in item.keys():
                val = item[key]
                if isinstance(val, (list, tuple)):
                    print(f"  {key}: list, len={len(val)}")
                    if len(val) > 0:
                        print(f"    第一个元素: {val[0]}")
                elif isinstance(val, str):
                    print(f"  {key}: str, len={len(val)}, 前100字符: {val[:100]}")
                else:
                    print(f"  {key}: {type(val).__name__}")
        elif isinstance(item, list):
            print(f"类型: list, len={len(item)}")
            if len(item) >= 2:
                print(f"  bbox: {item[0]}")
                print(f"  text_info: {item[1]}")
        else:
            print(f"类型: {type(item).__name__}")

# 重点查找 table/html/cell_bbox 字段
if result and result[0]:
    for item in result[0]:
        if isinstance(item, dict):
            if 'table' in item:
                print("\n=== table 字段 ===")
                table_data = item['table']
                print(f"类型: {type(table_data).__name__}")
                if isinstance(table_data, list):
                    print(f"行数: {len(table_data)}")
                    if len(table_data) > 0:
                        print(f"第一行: {table_data[0]}")
                elif isinstance(table_data, str):
                    print(f"HTML内容 (前500字符):\n{table_data[:500]}")
            
            if 'html' in item:
                print("\n=== html 字段 ===")
                print(f"内容 (前500字符):\n{item['html'][:500]}")
            
            if 'cell_bbox' in item:
                print("\n=== cell_bbox 字段 ===")
                cell_bbox = item['cell_bbox']
                print(f"类型: {type(cell_bbox).__name__}")
                if isinstance(cell_bbox, list):
                    print(f"数量: {len(cell_bbox)}")
                    if len(cell_bbox) > 0:
                        print(f"第一个bbox: {cell_bbox[0]}")

os.remove(temp_path)
doc.close()
