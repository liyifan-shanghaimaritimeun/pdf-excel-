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

# 模拟Y坐标聚合过程
sorted_cells = sorted(cells, key=lambda c: (c['center_y'], c['center_x']))

# 找出所有Y坐标聚类
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
            lines.append({
                'cy': current_y,
                'x0': min(c['x0'] for c in current_line),
                'x1': max(c['x1'] for c in current_line),
                'count': len(current_line),
                'texts': [c['text'] for c in current_line]
            })
        current_line = [cell]
        current_y = cy

if current_line:
    lines.append({
        'cy': current_y,
        'x0': min(c['x0'] for c in current_line),
        'x1': max(c['x1'] for c in current_line),
        'count': len(current_line),
        'texts': [c['text'] for c in current_line]
    })

print(f"Y坐标聚合后共 {len(lines)} 行")
print("\n行列表（按Y排序）:")
for i, line in enumerate(lines):
    print(f"  行{i}: y={line['cy']:.0f}, cells={line['count']}, x范围=[{line['x0']:.0f}-{line['x1']:.0f}]")
    if line['count'] <= 8:
        print(f"    texts: {line['texts'][:8]}")

# 现在模拟_infer_tables_from_lines
print("\n\n=== 模拟 _infer_tables_from_lines ===")
i = 0
while i < len(lines):
    table_lines = [lines[i]]
    j = i + 1
    first_line_h = max(lines[i]['x1'] - lines[i]['x0'], 1)
    
    while j < len(lines):
        gap = lines[j]['cy'] - lines[j-1]['cy']
        if gap <= first_line_h * 3.0:
            table_lines.append(lines[j])
            j += 1
        else:
            break
    
    if len(table_lines) >= 2:
        # 统计X坐标
        all_x = []
        for line in table_lines:
            all_x.append((line['x0'] + line['x1']) / 2)
        
        # X聚类
        sorted_x = sorted(all_x)
        diffs = [sorted_x[k+1] - sorted_x[k] for k in range(len(sorted_x)-1)]
        median_diff = sorted(diffs)[len(diffs) // 2] if diffs else 0
        gap_threshold = max(median_diff * 1.5, 20)
        
        clusters = [[sorted_x[0]]]
        for k in range(1, len(sorted_x)):
            if sorted_x[k] - sorted_x[k-1] > gap_threshold:
                clusters.append([sorted_x[k]])
            else:
                clusters[-1].append(sorted_x[k])
        
        col_count = len(clusters)
        
        # 检查是否跨全页
        all_x0 = [l['x0'] for l in table_lines]
        all_x1 = [l['x1'] for l in table_lines]
        table_width = max(all_x1) - min(all_x0)
        page_w = 5032  # 300dpi下宽度
        is_full_width = table_width > page_w * 0.85
        
        print(f"\n  候选表格: 行{i}-{j-1} ({len(table_lines)}行)")
        print(f"    行高: {first_line_h:.0f}px")
        print(f"    间距阈值: {first_line_h * 3.0:.0f}px")
        print(f"    X聚类数: {col_count}")
        print(f"    表格宽度: {table_width:.0f} (全页{page_w}的{table_width/page_w*100:.0f}%)")
        print(f"    是否全宽: {is_full_width}")
        
        # 判断逻辑
        if col_count >= 2:
            print(f"    → 多列，判定为表格 ✓")
        elif col_count == 1 and not is_full_width and len(table_lines) >= 3:
            print(f"    → 单列非全宽，判定为列表 ✓")
        else:
            print(f"    → 不满足表格条件 ✗")
    
    i = j if j > i + 1 else i + 1

doc.close()
extractor.close()
