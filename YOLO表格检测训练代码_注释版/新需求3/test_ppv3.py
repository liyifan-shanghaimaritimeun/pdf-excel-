"""
测试 PPStructureV3
"""
import sys, os, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from paddleocr import PPStructureV3, PPStructureV3Options

print(f"版本: {__import__('paddleocr').__version__}")

# 检查 PPStructureV3Options
print("\n=== PPStructureV3Options ===")
opts = PPStructureV3Options()
opt_attrs = [a for a in dir(opts) if not a.startswith('_')]
print(f"属性: {opt_attrs}")

# 初始化 PPStructureV3
print("\n=== 初始化 PPStructureV3 ===")
try:
    pp = PPStructureV3()
    print("初始化成功(默认)")
except Exception as e:
    print(f"默认初始化失败: {e}")
    try:
        pp = PPStructureV3(table=True)
        print("初始化成功(table=True)")
    except Exception as e2:
        print(f"table=True 初始化失败: {e2}")
        pp = PPStructureV3(options=PPStructureV3Options(table=True))
        print("初始化成功(options)")

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
print(f"页面渲染: {pix.width}x{pix.height}")

# 调用
print("\n=== 调用 PPStructureV3 ===")
try:
    result = pp.predict(temp_path)
    print(f"返回类型: {type(result)}")
    print(f"返回长度: {len(result)}")
    
    for i, item in enumerate(result):
        print(f"\n  结果项 {i}:")
        if isinstance(item, dict):
            keys = list(item.keys())
            print(f"    类型: dict, 键: {keys}")
            
            # 提取关键信息
            item_type = item.get('type', item.get('layout_type', 'unknown'))
            bbox = item.get('bbox', [])
            print(f"    type: {item_type}")
            print(f"    bbox: {bbox}")
            
            # 检查表格相关字段
            for key in ['html', 'cell_bbox', 'table', 'res', 'cells']:
                if key in item:
                    val = item[key]
                    if isinstance(val, str):
                        print(f"    {key}: str, len={len(val)}")
                        if len(val) < 500:
                            print(f"      内容: {val}")
                        else:
                            print(f"      前300字符: {val[:300]}")
                    elif isinstance(val, list):
                        print(f"    {key}: list, len={len(val)}")
                        if len(val) > 0:
                            elem = val[0]
                            if isinstance(elem, dict):
                                print(f"      [0] keys: {list(elem.keys())}")
                            elif isinstance(elem, list):
                                print(f"      [0] len: {len(elem)}, 前3: {elem[:3]}")
                            else:
                                print(f"      [0]: {elem}")
            
            # 如果有嵌套结构
            if 'layout' in item:
                layout = item['layout']
                if isinstance(layout, list):
                    print(f"    layout: list, len={len(layout)}")
        elif isinstance(item, list):
            print(f"    类型: list, len={len(item)}")
            if len(item) >= 2:
                print(f"    [0]: {item[0]}")
                print(f"    [1]: {item[1]}")
        else:
            print(f"    值: {str(item)[:200]}")
except Exception as e:
    print(f"异常: {e}")
    import traceback
    traceback.print_exc()

os.remove(temp_path)
doc.close()
