import sys, os, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import EnhancedPDFTableExtractor
import glob

# 测试拉拉乐
pattern = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\*拉拉乐*'
files = glob.glob(pattern)
pdf_path = files[0]
print(f"文件: {pdf_path}")

model_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_db')
extractor = EnhancedPDFTableExtractor(pdf_path, use_ocr=True, model_db_path=model_db_path)
import fitz
doc = fitz.open(pdf_path)

# 测试第13页
page_num = 12
page = doc.load_page(page_num)

result = extractor.ocr_extractor.scan_page_ppstructure(page, page_num, dpi=300)
cells = result.get('all_cells', [])
tables = result.get('tables', [])
out_cells = result.get('out_table_cells', [])

print(f"\n=== 页{page_num+1} ===")
print(f"OCR cells: {len(cells)}")
print(f"推断表格: {len(tables)}")
print(f"表外文字: {len(out_cells)}")

for i, t in enumerate(tables):
    d = t.get('data', [])
    bb = t.get('pixel_bbox', [])
    print(f"\n表格{i}: {len(d)}行 x {len(d[0]) if d and d[0] else 0}列")
    print(f"  bbox: {bb}")
    if d:
        for row in d[:3]:
            print(f"  {row[:8]}")

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

# 同时测试磁稳
print("\n" + "="*50)
print("测试磁稳PDF")
print("="*50)

import glob as gl
pattern2 = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\*磁稳*'
files2 = gl.glob(pattern2)
if files2:
    pdf_path2 = files2[0]
    extractor2 = EnhancedPDFTableExtractor(pdf_path2, use_ocr=True, model_db_path=model_db_path)
    doc2 = fitz.open(pdf_path2)
    
    for p in [4, 6, 7]:  # 测试几个有表格的页
        page = doc2.load_page(p)
        result2 = extractor2.ocr_extractor.scan_page_ppstructure(page, p, dpi=300)
        t2 = result2.get('tables', [])
        print(f"\n页{p+1}: 表格={len(t2)}")
        for ti in t2:
            d = ti.get('data', [])
            print(f"  {len(d)}行 x {len(d[0]) if d and d[0] else 0}列")
    
    doc2.close()
    extractor2.close()
