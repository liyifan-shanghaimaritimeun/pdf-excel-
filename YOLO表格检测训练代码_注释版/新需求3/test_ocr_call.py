import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import PDFTableExtractor

def test_ocr_call(pdf_path):
    print("=" * 70)
    print("OCR调用测试")
    print("=" * 70)
    print(f"测试文件: {pdf_path}")
    print()
    
    extractor = PDFTableExtractor(pdf_path, use_ocr=True)
    
    doc = __import__('fitz').open(pdf_path)
    total_pages = doc.page_count
    doc.close()
    
    print(f"总页数: {total_pages}")
    print()
    
    for page_num in range(min(3, total_pages)):
        print(f"第 {page_num + 1} 页:")
        
        is_scanned = extractor._is_scanned_pdf(page_num)
        print(f"  是否扫描件: {is_scanned}")
        
        tables_pymupdf = extractor._extract_with_pymupdf(page_num)
        print(f"  PyMuPDF识别表格数: {len(tables_pymupdf)}")
        
        if tables_pymupdf:
            for i, table in enumerate(tables_pymupdf):
                is_valid = extractor._is_pymupdf_result_valid(table)
                print(f"    表格{i+1}是否有效: {is_valid}")
        
        cells = extractor._get_ocr_cells(page_num)
        print(f"  OCR识别文字块数: {len(cells)}")
        
        if cells:
            print(f"  OCR识别耗时: 扫描件模式" if is_scanned else f"  OCR识别耗时: 普通模式")
        
        tables = extractor.extract_tables(page_num)
        print(f"  最终提取表格数: {len(tables)}")
        
        if tables:
            for i, table in enumerate(tables):
                print(f"    表格{i+1}: {len(table)}行 x {len(table[0])}列")
        
        print()

if __name__ == "__main__":
    pdf_path = "拉拉乐五金2026_扫描版_扫描版.pdf"
    
    if os.path.exists(pdf_path):
        test_ocr_call(pdf_path)
    else:
        print(f"文件不存在: {pdf_path}")
