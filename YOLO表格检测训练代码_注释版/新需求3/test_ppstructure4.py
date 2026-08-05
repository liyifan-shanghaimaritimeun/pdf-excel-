"""
测试 PPStructure 不同配置
"""
import sys, os, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from paddleocr import PPStructure

# 测试不同配置
configs = [
    {"table": True, "ocr": True, "show_log": False},
    {"table": True, "ocr": True, "show_log": False, "table_model": "slanet_seresnet18"},
]

pdf_path = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\磁稳产品手册(2025版).pdf'
doc = fitz.open(pdf_path)
page_num = 6
page = doc.load_page(page_num)
dpi = 300
pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
temp_path = "test_page.png"
pix.save(temp_path)

for cfg in configs:
    print(f"\n{'='*60}")
    print(f"配置: {cfg}")
    print(f"{'='*60}")
    
    try:
        pp = PPStructure(**cfg)
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
                
                if item_type == 'table':
                    print(f"    *** 检测到表格! ***")
                    print(f"    res 长度: {len(res)}")
                    if res:
                        first_res = res[0]
                        if isinstance(first_res, dict):
                            print(f"    res[0] 键: {list(first_res.keys())}")
                            if 'html' in first_res:
                                html = first_res['html']
                                print(f"    html (前300字符): {html[:300]}")
                            if 'cell_bbox' in first_res:
                                print(f"    cell_bbox 数量: {len(first_res['cell_bbox'])}")
                        elif isinstance(first_res, list):
                            print(f"    res[0] 是list, len={len(first_res)}")
                            print(f"    res[0][0] = {first_res[0]}")
                elif res:
                    print(f"    res: {len(res)} 项")
                    if len(res) <= 3:
                        for j, r in enumerate(res):
                            if isinstance(r, dict):
                                print(f"      res[{j}]: {list(r.keys())}")
    except Exception as e:
        print(f"异常: {e}")
        import traceback
        traceback.print_exc()

os.remove(temp_path)
doc.close()
