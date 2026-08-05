"""
测试 PPStructureV3 正确参数
"""
import sys, os, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from paddleocr import PPStructureV3, PPStructureV3Options

print(f"版本: {__import__('paddleocr').__version__}")

# 正确参数: use_table_recognition=True
print("\n=== 初始化 PPStructureV3 (use_table_recognition=True) ===")
try:
    pp = PPStructureV3(
        options=PPStructureV3Options(
            use_table_recognition=True,
            use_region_detection=True,
        )
    )
    print("初始化成功")
except Exception as e:
    print(f"初始化失败: {e}")
    # 尝试默认
    print("尝试默认初始化...")
    pp = PPStructureV3()
    print("默认初始化成功")

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
print("\n=== 调用 PPStructureV3.predict ===")
try:
    result = pp.predict(temp_path)
    print(f"返回类型: {type(result)}")
    print(f"返回长度: {len(result)}")
    
    for i, item in enumerate(result):
        print(f"\n  结果项 {i}:")
        if isinstance(item, dict):
            keys = list(item.keys())
            print(f"    键: {keys}")
            
            item_type = item.get('type', item.get('layout_type', 'unknown'))
            bbox = item.get('bbox', [])
            print(f"    type: {item_type}")
            print(f"    bbox: {bbox}")
            
            # 检查表格字段
            for key in ['html', 'cell_bbox', 'table', 'cells', 'res']:
                if key in item:
                    val = item[key]
                    if isinstance(val, str):
                        print(f"    {key}: str, len={len(val)}")
                        if 'table' in item_type.lower() or 'table' in str(item_type).lower():
                            print(f"      内容:\n{val[:500]}")
                    elif isinstance(val, list):
                        print(f"    {key}: list, len={len(val)}")
                        if len(val) > 0:
                            elem = val[0]
                            if isinstance(elem, dict):
                                print(f"      [0] keys: {list(elem.keys())}")
                                # 检查嵌套结构
                                for nk in elem.keys():
                                    if nk in ['html', 'cell_bbox', 'table']:
                                        nv = elem[nk]
                                        if isinstance(nv, str):
                                            print(f"        {nk}: str, len={len(nv)}")
                                            if 'table' in str(item_type).lower():
                                                print(f"          {nv[:300]}")
                                        elif isinstance(nv, list):
                                            print(f"        {nk}: list, len={len(nv)}")
                                            if len(nv) > 0:
                                                print(f"          [0]: {nv[0]}")
                            elif isinstance(elem, list):
                                print(f"      [0]: list, len={len(elem)}")
                                if len(elem) > 0 and len(elem[0]) > 0:
                                    print(f"        [0][0]: {elem[0][0]}")
    pass
except Exception as e:
    print(f"异常: {e}")
    import traceback
    traceback.print_exc()

os.remove(temp_path)
doc.close()
