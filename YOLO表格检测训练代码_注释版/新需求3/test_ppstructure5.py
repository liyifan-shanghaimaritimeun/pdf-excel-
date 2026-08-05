"""
测试 PPStructure 3.7.0
"""
import sys, os, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from paddleocr import PPStructure

print("=== paddleocr 3.7.0 测试 ===")

# 初始化
print("初始化 PPStructure(table=True)...")
try:
    pp = PPStructure(table=True, ocr=True, show_log=False)
    print("初始化成功")
except Exception as e:
    print(f"初始化失败: {e}")
    # 尝试不带table
    print("尝试不带table参数...")
    pp = PPStructure(show_log=False)
    print("初始化成功(不带table)")

# 测试两个PDF
pdfs = [
    (r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\磁稳产品手册(2025版).pdf', 6, 7),
    (r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\拉拉乐五金2026.pdf', 12, 13),
]

for pdf_path, page_num, page_display in pdfs:
    print(f"\n{'='*60}")
    print(f"测试: {os.path.basename(pdf_path)} 第{page_display}页")
    print(f"{'='*60}")
    
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    dpi = 300
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
    temp_path = "test_page_temp.png"
    pix.save(temp_path)
    print(f"页面渲染: {pix.width}x{pix.height}")
    
    try:
        result = pp(temp_path)
        print(f"返回长度: {len(result)}")
        
        for i, item in enumerate(result):
            if isinstance(item, dict):
                item_type = item.get('type', 'unknown')
                bbox = item.get('bbox', [])
                score = item.get('score', 0)
                res = item.get('res', [])
                
                print(f"\n  结果项 {i}: type={item_type}, score={score:.3f}")
                print(f"    bbox: {bbox}")
                
                if item_type == 'table' or (isinstance(item_type, str) and 'table' in item_type.lower()):
                    print(f"    *** 检测到表格! ***")
                    if res:
                        first_res = res[0]
                        if isinstance(first_res, dict):
                            print(f"    res[0] 键: {list(first_res.keys())}")
                            if 'html' in first_res:
                                html = first_res['html']
                                print(f"    html (前500字符):\n{html[:500]}")
                            if 'cell_bbox' in first_res:
                                print(f"    cell_bbox 数量: {len(first_res['cell_bbox'])}")
                            if 'table' in first_res:
                                table_data = first_res['table']
                                print(f"    table 字段: {type(table_data).__name__}")
                                if isinstance(table_data, list):
                                    print(f"    行数: {len(table_data)}")
                                    if len(table_data) > 0:
                                        print(f"    第一行: {table_data[0]}")
                        elif isinstance(first_res, list):
                            print(f"    res[0] 是list, len={len(first_res)}")
                            if len(first_res) > 0:
                                print(f"    res[0][0] = {first_res[0]}")
                
                # 打印非表格项的res内容
                if item_type != 'table' and res and len(res) <= 3:
                    print(f"    res 摘要 ({len(res)}项):")
                    for j, r in enumerate(res):
                        if isinstance(r, dict):
                            text = r.get('text', '')
                            conf = r.get('confidence', 0)
                            print(f"      [{j}] text='{text[:50]}', conf={conf:.3f}")
    except Exception as e:
        print(f"异常: {e}")
        import traceback
        traceback.print_exc()
    
    os.remove(temp_path)
    doc.close()
