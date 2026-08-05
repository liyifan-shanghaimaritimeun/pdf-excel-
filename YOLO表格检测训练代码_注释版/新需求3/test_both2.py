import sys, os, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import EnhancedPDFTableExtractor
import glob

# 测试拉拉乐
lalale_files = glob.glob(r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\*拉拉乐*')
if lalale_files:
    print("=" * 60)
    print("测试拉拉乐PDF")
    print("=" * 60)
    pdf_path = lalale_files[0]
    model_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_db')
    extractor = EnhancedPDFTableExtractor(pdf_path, use_ocr=True, model_db_path=model_db_path)
    import fitz
    doc = fitz.open(pdf_path)
    
    page_num = 12  # 第13页
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
        print(f"表格{i}: {t.get('line_count',0)}行 x {t.get('col_count',0)}列")
    
    full = extractor.extract_with_table_alignment(page_num)
    full_tables = full.get('tables', [])
    print(f"\n完整提取: {len(full_tables)} 个表格")
    for i, t in enumerate(full_tables):
        d = t.get('data', [])
        src = t.get('source', '')
        print(f"提取表格{i}: {len(d)}行 x {len(d[0]) if d and d[0] else 0}列, source={src}")
        if d:
            for row in d[:2]:
                print(f"  {row[:8]}")
    
    doc.close()
    extractor.close()

# 测试磁稳
ciwen_files = glob.glob(r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\*磁稳*')
if ciwen_files:
    print("\n" + "=" * 60)
    print("测试磁稳PDF")
    print("=" * 60)
    pdf_path = ciwen_files[0]
    model_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model_db')
    extractor = EnhancedPDFTableExtractor(pdf_path, use_ocr=True, model_db_path=model_db_path)
    import fitz
    doc = fitz.open(pdf_path)
    
    # 测试多页
    for page_num in [4, 6, 7]:  # 页5, 7, 8
        page = doc.load_page(page_num)
        result = extractor.ocr_extractor.scan_page_ppstructure(page, page_num, dpi=300)
        tables = result.get('tables', [])
        print(f"\n页{page_num+1}: 表格={len(tables)}")
        for i, t in enumerate(tables):
            print(f"  {t.get('line_count',0)}行 x {t.get('col_count',0)}列")
    
    doc.close()
    extractor.close()
