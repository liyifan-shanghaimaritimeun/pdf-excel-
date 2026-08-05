import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import PDFTableExtractor

def debug_table_recognition(pdf_path):
    print("=" * 70)
    print("表格识别调试工具")
    print("=" * 70)
    
    extractor = PDFTableExtractor(pdf_path, use_ocr=True)
    
    doc = __import__('fitz').open(pdf_path)
    total_pages = doc.page_count
    doc.close()
    
    for page_num in range(total_pages):
        print(f"\n{'=' * 70}")
        print(f"第 {page_num + 1} 页")
        print(f"{'=' * 70}")
        
        print("\n--- PyMuPDF 表格提取 ---")
        tables_pymupdf = extractor._extract_with_pymupdf(page_num)
        print(f"PyMuPDF 识别到 {len(tables_pymupdf)} 个表格")
        
        for i, table in enumerate(tables_pymupdf):
            print(f"\n表格 {i+1}: {len(table)}行 x {len(table[0])}列")
            for j, row in enumerate(table[:5]):
                print(f"  行{j}: {row}")
        
        print("\n--- OCR 识别 ---")
        cells = extractor._get_ocr_cells(page_num)
        print(f"OCR 识别到 {len(cells)} 个文字块")
        
        if cells:
            print("\n前20个文字块：")
            for j, cell in enumerate(cells[:20]):
                print(f"  [{j}] text='{cell['text']}' x0={cell['x0']:.1f} y0={cell['y0']:.1f} x1={cell['x1']:.1f} y1={cell['y1']:.1f}")
        
        print("\n--- OCR行聚类 ---")
        rows = extractor._cluster_by_rows(cells)
        print(f"聚类得到 {len(rows)} 行")
        
        if rows:
            print("\n前5行的单元格数量：")
            for j, row in enumerate(rows[:5]):
                cell_texts = [c['text'] for c in row]
                print(f"  行{j}: {len(row)}个单元格 - {cell_texts}")
        
        print("\n--- 列检测 ---")
        if rows:
            column_x = extractor._detect_columns(rows)
            print(f"检测到 {len(column_x)} 列，X坐标: {[round(x, 1) for x in column_x]}")
        
        print("\n--- 最终表格提取 ---")
        tables = extractor.extract_tables(page_num)
        print(f"最终提取到 {len(tables)} 个表格")
        
        for i, table in enumerate(tables):
            print(f"\n表格 {i+1}: {len(table)}行 x {len(table[0])}列")
            print("表格内容：")
            for j, row in enumerate(table):
                print(f"  {j}: {row}")

if __name__ == "__main__":
    pdf_path = os.path.join("拉拉乐五金2026_扫描版_扫描版.pdf")
    
    if os.path.exists(pdf_path):
        print(f"测试PDF文件: {pdf_path}")
        debug_table_recognition(pdf_path)
    else:
        print(f"文件不存在: {pdf_path}")
        import glob
        pdf_files = glob.glob(os.path.join(".", "*扫描*.pdf"))
        print(f"可用PDF文件: {pdf_files}")
