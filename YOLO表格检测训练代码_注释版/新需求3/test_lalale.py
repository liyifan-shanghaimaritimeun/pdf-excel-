import sys, os, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import EnhancedPDFTableExtractor
import fitz

# 找拉拉乐PDF
import glob
pattern = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\*拉拉乐*'
files = glob.glob(pattern)
if not files:
    pattern2 = r'C:\Users\admin\Desktop\测试数据\测试数据\**\*拉拉乐*'
    files = glob.glob(pattern2, recursive=True)

if not files:
    print("找不到拉拉乐PDF！")
    sys.exit(1)

pdf_path = files[0]
print(f"文件: {pdf_path}")

model_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_db')
extractor = EnhancedPDFTableExtractor(pdf_path, use_ocr=True, model_db_path=model_db_path)

doc = fitz.open(pdf_path)
print(f"总页数: {len(doc)}")

# 第13页（索引12）
page_num = 12
page = doc.load_page(page_num)
is_scanned = extractor._is_scanned_pdf(page_num)
text = page.get_text()

print(f"\n=== 页{page_num+1} (扫描={is_scanned}) ===")
print(f"  矢量文字长度: {len(text.strip())}")

# 先看OCR识别的原始cells
result = extractor.ocr_extractor.scan_page_ppstructure(page, page_num, dpi=300)
cells = result.get('all_cells', [])
tables = result.get('tables', [])
out_cells = result.get('out_table_cells', [])

print(f"  OCR cells总数: {len(cells)}")
print(f"  推断表格数: {len(tables)}")
print(f"  表外文字: {len(out_cells)}")

# 打印所有表格
for i, t in enumerate(tables):
    d = t.get('data', [])
    bb = t.get('pixel_bbox', [])
    print(f"\n  表格{i}: {len(d)}行 x {len(d[0]) if d and d[0] else 0}列")
    print(f"    bbox(像素): {bb}")
    if d:
        print(f"    第1行: {d[0][:6]}")
        if len(d) > 1:
            print(f"    第2行: {d[1][:6]}")

# 打印右下角区域的cells
print("\n  === 右下角区域cells ===")
pix = page.get_pixmap(matrix=fitz.Matrix(300/72.0, 300/72.0))
page_w = pix.width
page_h = pix.height
right_bottom_cells = [c for c in cells if c['center_x'] > page_w * 0.4 and c['center_y'] > page_h * 0.4]
print(f"  右下角({page_w*0.4:.0f}x{page_h*0.4:.0f} 以下)cells: {len(right_bottom_cells)}")

# 按Y坐标分组打印
right_bottom_cells.sort(key=lambda c: (c['center_y'], c['center_x']))
if right_bottom_cells:
    print("  内容:")
    for c in right_bottom_cells[:30]:
        print(f"    ({c['center_x']:.0f},{c['center_y']:.0f}) [{c['x0']:.0f}-{c['x1']:.0f}x{c['y0']:.0f}-{c['y1']:.0f}] {c['text'][:60]}")

# 调用完整提取
print("\n  === 完整提取 ===")
full_result = extractor.extract_with_table_alignment(page_num)
full_tables = full_result.get('tables', [])
for i, t in enumerate(full_tables):
    d = t.get('data', [])
    src = t.get('source', '')
    print(f"  提取表格{i}: {len(d)}行 x {len(d[0]) if d and d[0] else 0}列, source={src}")

doc.close()
extractor.close()
