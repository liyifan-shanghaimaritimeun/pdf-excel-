import sys, os, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import EnhancedPDFTableExtractor
import glob

pattern = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\*拉拉乐*'
files = glob.glob(pattern)
pdf_path = files[0]

model_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_db')
extractor = EnhancedPDFTableExtractor(pdf_path, use_ocr=True, model_db_path=model_db_path)
import fitz
doc = fitz.open(pdf_path)

page_num = 12
page = doc.load_page(page_num)
result = extractor.ocr_extractor.scan_page_ppstructure(page, page_num, dpi=300)
cells = result.get('all_cells', [])

# 模拟Y坐标聚合
sorted_cells = sorted(cells, key=lambda c: (c['center_y'], c['center_x']))

# 聚合为lines
lines = []
current_line = []
current_y = None
y_tolerance = 15

for cell in sorted_cells:
    cy = cell['center_y']
    if current_y is None:
        current_y = cy
        current_line.append(cell)
    elif abs(cy - current_y) <= y_tolerance:
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

# 显示每行的cell_count
print("行列表 (cell_count >= 2):")
for i, l in enumerate(lines):
    cc = len(l.get('cells', []))
    if cc >= 2:
        print(f"  行{i}: y0={l['y0']:.0f}-y1={l['y1']:.0f}, cells={cc}, x=[{l['x0']:.0f}-{l['x1']:.0f}]")
        print(f"    texts: {[c['text'][:20] for c in l.get('cells', [])[:8]]}")

# 调用推断
print("\n=== 调用 _infer_tables_from_lines ===")
tables = extractor.ocr_extractor._infer_tables_from_lines(lines)
print(f"推断表格数: {len(tables)}")
for i, t in enumerate(tables):
    print(f"  表格{i}: {t.get('line_count')}行, {t.get('col_count')}列")
    print(f"    bbox: {t.get('bbox')}")

# 如果没检测到，手动检查
if not tables:
    print("\n=== 手动检查 ===")
    # 找cell_count >= 3的特征行
    feature_indices = [i for i, l in enumerate(lines) if len(l.get('cells', [])) >= 3]
    print(f"cell_count>=3的特征行: {len(feature_indices)} 个")
    for idx in feature_indices:
        l = lines[idx]
        print(f"  行{idx}: y0={l['y0']:.0f}, cells={len(l.get('cells', []))}, x=[{l['x0']:.0f}-{l['x1']:.0f}]")
    
    # 检查特征行之间的间距
    if len(feature_indices) >= 2:
        print("\n特征行间距检查:")
        for k in range(1, len(feature_indices)):
            gap = feature_indices[k] - feature_indices[k-1]
            if gap > 4:
                print(f"  警告: 行{feature_indices[k-1]}到行{feature_indices[k]}间距={gap} (>4)")

doc.close()
extractor.close()
