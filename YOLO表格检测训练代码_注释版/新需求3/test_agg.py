import sys, os, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import EnhancedPDFTableExtractor
import glob

pattern = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\*磁稳*'
files = glob.glob(pattern)
pdf_path = files[0]

model_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_db')
extractor = EnhancedPDFTableExtractor(pdf_path, use_ocr=True, model_db_path=model_db_path)
import fitz
doc = fitz.open(pdf_path)

page_num = 6
page = doc.load_page(page_num)
result = extractor.ocr_extractor.scan_page_ppstructure(page, page_num, dpi=300)
cells = result.get('all_cells', [])

# 手动模拟Y坐标聚合
sorted_cells = sorted(cells, key=lambda c: (c['center_y'], c['center_x']))

# 用不同的Y容差测试
for y_tol in [10, 15, 20, 25, 30]:
    lines = []
    current_line = []
    current_y = None
    
    for cell in sorted_cells:
        cy = cell['center_y']
        if current_y is None:
            current_y = cy
            current_line.append(cell)
        elif abs(cy - current_y) <= y_tol:
            current_line.append(cell)
            current_y = sum(c['center_y'] for c in current_line) / len(current_line)
        else:
            if current_line:
                lines.append(extractor.ocr_extractor._merge_cells_to_line(current_line))
            current_line = [cell]
            current_y = cy
    
    if current_line:
        lines.append(extractor.ocr_extractor._merge_cells_to_line(current_line))
    
    lines = [l for l in lines if l]
    
    # 统计cell_count分布
    cc_dist = {}
    for l in lines:
        cc = len(l.get('cells', []))
        cc_dist[cc] = cc_dist.get(cc, 0) + 1
    
    print(f"Y容差={y_tol}: {len(lines)}行, cell_count分布: {dict(sorted(cc_dist.items()))}")
    
    # 对于Y容差=15，显示有>=3 cells的行
    if y_tol == 15:
        print("\ncell_count>=3的行:")
        for i, l in enumerate(lines):
            cc = len(l.get('cells', []))
            if cc >= 3:
                texts = [c['text'][:15] for c in l.get('cells', [])[:10]]
                print(f"  行{i}: y={l['y0']:.0f}-{l['y1']:.0f}, cells={cc}, texts={texts}")

doc.close()
extractor.close()
