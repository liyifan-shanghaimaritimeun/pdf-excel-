import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import PDFTableExtractor

def debug_full_extraction(pdf_path, model_dir):
    logger.info("=" * 70)
    logger.info("完整提取流程调试")
    logger.info("=" * 70)
    logger.info(f"PDF文件: {pdf_path}")
    logger.info(f"模型目录: {model_dir}")
    logger.info(f"模型目录存在: {os.path.isdir(model_dir) if model_dir else False}")
    logger.info("")
    
    try:
        logger.info("创建PDFTableExtractor...")
        extractor = PDFTableExtractor(pdf_path, use_ocr=True, model_dir=model_dir)
        
        logger.info(f"use_ocr: {extractor.use_ocr}")
        logger.info(f"model_dir: {extractor.model_dir}")
        
        logger.info("调用_init_ocr_if_needed...")
        try:
            extractor._init_ocr_if_needed()
            logger.info("_init_ocr_if_needed调用完成")
        except Exception as e:
            logger.error(f"_init_ocr_if_needed出错: {e}", exc_info=True)
        
        if extractor.ocr_extractor:
            logger.info(f"OCR提取器类型: {type(extractor.ocr_extractor)}")
            if extractor.ocr_extractor.ocr:
                logger.info("✓ OCR已初始化")
            else:
                logger.info("✗ OCR未初始化")
        else:
            logger.info("✗ OCR提取器未创建")
        
        logger.info("")
        
        import fitz
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()
        logger.info(f"总页数: {total_pages}")
        
        test_page = 0
        logger.info(f"\n测试第 {test_page + 1} 页:")
        
        is_scanned = extractor._is_scanned_pdf(test_page)
        logger.info(f"是否扫描件: {is_scanned}")
        
        tables_pymupdf = extractor._extract_with_pymupdf(test_page)
        logger.info(f"PyMuPDF识别表格数: {len(tables_pymupdf)}")
        
        for i, table in enumerate(tables_pymupdf):
            is_valid = extractor._is_pymupdf_result_valid(table)
            logger.info(f"  表格{i+1}是否有效: {is_valid}")
            if table:
                logger.info(f"  表格{i+1}: {len(table)}行 x {len(table[0])}列")
        
        if extractor.ocr_extractor:
            logger.info("\n获取OCR单元格...")
            cells = extractor._get_ocr_cells(test_page)
            logger.info(f"OCR识别文字块数: {len(cells)}")
            
            if cells:
                for i, cell in enumerate(cells[:5]):
                    logger.info(f"  [{i}] text='{cell['text'][:30]}...' pos=({cell['x0']:.1f},{cell['y0']:.1f})-({cell['x1']:.1f},{cell['y1']:.1f})")
            
            logger.info("\n提取表格...")
            tables = extractor.extract_tables(test_page)
            logger.info(f"最终提取表格数: {len(tables)}")
            
            for i, table in enumerate(tables):
                logger.info(f"  表格{i+1}: {len(table)}行 x {len(table[0])}列")
                for j, row in enumerate(table[:3]):
                    row_str = " | ".join([str(cell)[:20] for cell in row])
                    logger.info(f"    行{j+1}: {row_str}")
        else:
            logger.error("OCR提取器未创建，无法进行OCR提取")
            
    except Exception as e:
        logger.error(f"提取过程出错: {e}", exc_info=True)

if __name__ == "__main__":
    pdf_path = "拉拉乐五金2026_扫描版_扫描版.pdf"
    model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "测试", "models")
    
    if os.path.exists(pdf_path):
        debug_full_extraction(pdf_path, model_dir)
    else:
        logger.error(f"文件不存在: {pdf_path}")
        import glob
        pdf_files = glob.glob(os.path.join(".", "*扫描*.pdf"))
        logger.info(f"可用PDF文件: {pdf_files}")
