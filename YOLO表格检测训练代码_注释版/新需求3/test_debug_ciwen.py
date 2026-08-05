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

# 模拟Y坐标聚合 (y_tol=15)
sorted_cells = sorted(cells, key=lambda c: (c['center_y'], c['center_x']))
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

# 计算cell_count
for line in lines:
    line['cell_count'] = len(line.get('cells', []))

# 估算页面宽度
page_x0 = min(l['x0'] for l in lines)
page_x1 = max(l['x1'] for l in lines)
page_width = page_x1 - page_x0
full_width_threshold = page_width * 0.8

print(f"页面宽度: {page_width:.0f}, 全宽阈值: {full_width_threshold:.0f}")

# 显示cell_count>=3的行的X范围
print("\ncell_count>=3的行:")
for i, l in enumerate(lines):
    if l['cell_count'] >= 3:
        line_width = l['x1'] - l['x0']
        is_full = line_width >= full_width_threshold
        print(f"  行{i}: y=[{l['y0']:.0f}-{l['y1']:.0f}], cells={l['cell_count']}, x=[{l['x0']:.0f}-{l['x1']:.0f}], width={line_width:.0f}, 全宽={is_full}")

# 手动调用推断
print("\n=== 调用 _infer_tables_from_lines ===")
tables = extractor.ocr_extractor._infer_tables_from_lines(lines)
print(f"推断表格数: {len(tables)}")

# 手动模拟过滤和分组
print("\n=== 手动模拟 ===")
filtered_lines = []
for i, line in enumerate(lines):
    line_width = line['x1'] - line['x0']
    is_full = line_width >= full_width_threshold
    if not is_full:
        filtered_lines.append(line)

print(f"过滤后: {len(filtered_lines)} 行 (全宽过滤掉 {len(lines) - len(filtered_lines)} 行)")

feature_indices = [i for i, l in enumerate(filtered_lines) if l['cell_count'] >= 3]
print(f"特征行(cell_count>=3): {len(feature_indices)} 个")
for idx in feature_indices:
    l = filtered_lines[idx]
    line_width = l['x1'] - l['x0']
    print(f"  索引{idx}: y=[{l['y0']:.0f}-{l['y1']:.0f}], cells={l['cell_count']}, x=[{l['x0']:.0f}-{l['x1']:.0f}], width={line_width:.0f}")

# 检查相邻特征行的X重叠度
print("\n相邻特征行X重叠检查:")
for k in range(1, len(feature_indices)):
    idx = feature_indices[k]
    prev_idx = feature_indices[k-1]
    y_gap = idx - prev_idx
    
    prev_line = filtered_lines[prev_idx]
    curr_line = filtered_lines[idx]
    prev_x0, prev_x1 = prev_line['x0'], prev_line['x1']
    curr_x0, curr_x1 = curr_line['x0'], curr_line['x1']
    
    overlap_x0 = max(prev_x0, curr_x0)
    overlap_x1 = min(prev_x1, curr_x1)
    overlap = max(0, overlap_x1 - overlap_x0)
    min_width = min(prev_x1 - prev_x0, curr_x1 - curr_x0)
    overlap_ratio = overlap / min_width if min_width > 0 else 0
    
    print(f"  {prev_idx}->{idx}: y_gap={y_gap}, overlap={overlap:.0f}, min_width={min_width:.0f}, ratio={overlap_ratio:.2f}")

doc.close()
extractor.close()
