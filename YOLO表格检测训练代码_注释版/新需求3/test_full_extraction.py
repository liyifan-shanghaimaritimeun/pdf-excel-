import os
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import PDFTableExtractor

def test_full_extraction(pdf_path, model_dir):
    print("=" * 70)
    print("完整提取流程测试")
    print("=" * 70)
    print(f"PDF文件: {pdf_path}")
    print(f"模型目录: {model_dir}")
    print()
    
    start_time = time.time()
    
    try:
        print("1. 创建PDFTableExtractor...")
        extractor = PDFTableExtractor(pdf_path, use_ocr=True, model_dir=model_dir)
        print("   ✓ 创建成功")
        
        print("\n2. 初始化OCR...")
        extractor._init_ocr_if_needed()
        if extractor.ocr_extractor and extractor.ocr_extractor.ocr:
            print("   ✓ OCR初始化成功")
        else:
            print("   ✗ OCR初始化失败")
            return
        
        print("\n3. 测试第1页提取...")
        is_scanned = extractor._is_scanned_pdf(23)
        print(f"   是否扫描件: {is_scanned}")
        
        tables_pymupdf = extractor._extract_with_pymupdf(23)
        print(f"   PyMuPDF识别表格数: {len(tables_pymupdf)}")
        
        print("\n4. 调用extract_tables...")
        tables = extractor.extract_tables(23)
        print(f"   最终提取表格数: {len(tables)}")
        
        if tables:
            for i, table in enumerate(tables):
                print(f"   表格{i+1}: {len(table)}行 x {len(table[0])}列")
                for j, row in enumerate(table[:3]):
                    row_str = " | ".join([str(cell)[:20] for cell in row])
                    print(f"     行{j+1}: {row_str}")
        
        elapsed_time = time.time() - start_time
        print(f"\n✓ 测试完成，耗时: {elapsed_time:.2f}秒")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n✗ 测试失败，耗时: {elapsed_time:.2f}秒")
        print(f"   错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    pdf_path = "拉拉乐五金2026_扫描版_扫描版.pdf"
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "测试", "models")
    
    if os.path.exists(pdf_path):
        test_full_extraction(pdf_path, model_dir)
    else:
        print(f"文件不存在: {pdf_path}")
