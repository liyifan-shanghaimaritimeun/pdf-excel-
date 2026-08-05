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

# 手动模拟
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

print(f"页面宽度估算: {page_width:.0f}, 全宽阈值: {full_width_threshold:.0f}")

# 过滤全宽行
filtered_lines = []
for i, line in enumerate(lines):
    line_width = line['x1'] - line['x0']
    is_full = line_width >= full_width_threshold
    print(f"行{i}: cells={line['cell_count']}, width={line_width:.0f}, 全宽={is_full}")
    if not is_full:
        filtered_lines.append(line)

print(f"\n过滤后: {len(filtered_lines)} 行")

# 找特征行
feature_indices = [i for i, l in enumerate(filtered_lines) if l['cell_count'] >= 3]
print(f"特征行(>=3 cells): {len(feature_indices)} 个")
for idx in feature_indices:
    l = filtered_lines[idx]
    print(f"  过滤后索引{idx}: cells={l['cell_count']}, y0={l['y0']:.0f}, x=[{l['x0']:.0f}-{l['x1']:.0f}]")

# 组合特征行
if len(feature_indices) >= 2:
    groups = []
    current_group = [feature_indices[0]]
    for k in range(1, len(feature_indices)):
        idx = feature_indices[k]
        prev_idx = feature_indices[k-1]
        gap = idx - prev_idx
        if gap <= 4:
            current_group.append(idx)
        else:
            if len(current_group) >= 2:
                groups.append(current_group)
            current_group = [idx]
    if len(current_group) >= 2:
        groups.append(current_group)
    
    print(f"\n分组: {len(groups)} 组")
    for gi, group in enumerate(groups):
        print(f"  组{gi}: {len(group)} 行, 索引={group}")
        table_lines = [filtered_lines[i] for i in group]
        col_count = extractor.ocr_extractor._count_x_columns(table_lines)
        print(f"    列数: {col_count}")
        
        # 计算bbox
        all_x0 = [l['x0'] for l in table_lines]
        all_x1 = [l['x1'] for l in table_lines]
        bbox_width = max(all_x1) - min(all_x0)
        print(f"    宽度: {bbox_width:.0f} (全页{page_width}的{bbox_width/page_width*100:.0f}%)")

doc.close()
extractor.close()
