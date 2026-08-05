import sys, os, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import EnhancedPDFTableExtractor

pdf_path = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\磁稳产品手册(2025版).pdf'
model_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_db')

extractor = EnhancedPDFTableExtractor(pdf_path, use_ocr=True, model_db_path=model_db_path)
print(f'总页数: {len(extractor.doc)}')
print(f'OCR引擎: {extractor.ocr_extractor.ocr is not None}')

# 测试前10页
for p in range(min(10, len(extractor.doc))):
    is_scanned = extractor._is_scanned_pdf(p)
    result = extractor.extract_with_table_alignment(p)
    
    tbls = result.get('tables', [])
    out_models = result.get('out_table_models', [])
    conserv = result.get('conservation', {})
    
    tbl_info = ''
    for t in tbls:
        d = t.get('data', [])
        tbl_info += f' {len(d)}行x{len(d[0]) if d and d[0] else 0}列'
    
    print(f'页{p+1}(扫描={is_scanned}): 表格={len(tbls)}[{tbl_info.strip()}], 表外型号={len(out_models)}, 守恒={conserv.get("ok")}')

extractor.close()
