import sys, os, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import EnhancedPDFTableExtractor
import glob

pattern = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\*磁稳*'
files = glob.glob(pattern)
pdf_path = files[0]
print(f"文件: {pdf_path}")

model_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_db')
extractor = EnhancedPDFTableExtractor(pdf_path, use_ocr=True, model_db_path=model_db_path)
import fitz
doc = fitz.open(pdf_path)

# 测试第7页（索引6）
page_num = 6
page = doc.load_page(page_num)

result = extractor.ocr_extractor.scan_page_ppstructure(page, page_num, dpi=300)
cells = result.get('all_cells', [])
tables = result.get('tables', [])
out_cells = result.get('out_table_cells', [])

print(f"\n=== 页{page_num+1} ===")
print(f"OCR cells: {len(cells)}")
print(f"推断表格: {len(tables)}")
print(f"表外文字: {len(out_cells)}")

# 显示前30个cells
print("\n前30个OCR cells:")
cells_sorted = sorted(cells, key=lambda c: (c['center_y'], c['center_x']))
for c in cells_sorted[:30]:
    print(f"  y={c['center_y']:.0f}, x={c['center_x']:.0f}, [{c['x0']:.0f}-{c['x1']:.0f}] cells_in_line=?, text={c['text'][:40]}")

# 完整提取
print("\n=== 完整提取 ===")
full = extractor.extract_with_table_alignment(page_num)
full_tables = full.get('tables', [])
for i, t in enumerate(full_tables):
    d = t.get('data', [])
    src = t.get('source', '')
    print(f"提取表格{i}: {len(d)}行 x {len(d[0]) if d and d[0] else 0}列, source={src}")
    if d:
        for row in d[:3]:
            print(f"  {row[:8]}")

doc.close()
extractor.close()
