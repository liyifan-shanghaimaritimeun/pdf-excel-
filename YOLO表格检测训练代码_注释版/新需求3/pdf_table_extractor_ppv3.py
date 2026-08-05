"""
PDF表格数据提取器 - PP-StructureV3版本

核心功能：
1. 使用PyMuPDF(fitz)进行PDF页面渲染
2. 使用PaddleOCR的PPStructure进行表格识别
3. 自动保存扫描图片到文件夹
4. 将识别结果导出为Excel
"""

import os
import re
import threading
import fitz
import pandas as pd
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from html.parser import HTMLParser


class TableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = []
        self.current_row = []
        self.current_cell = []
        self.in_table = False
        self.in_row = False
        self.in_cell = False
    
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
            self.current_table = []
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ('td', 'th') and self.in_row:
            self.in_cell = True
            self.current_cell = []
    
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
            if self.current_table:
                self.tables.append(self.current_table)
        elif tag == 'tr' and self.in_table:
            self.in_row = False
            if self.current_row:
                self.current_table.append(self.current_row)
        elif tag in ('td', 'th') and self.in_row:
            self.in_cell = False
            cell_text = ''.join(self.current_cell).strip()
            self.current_row.append(cell_text)
            self.current_cell = []
    
    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)


class PPStructureV3Extractor:
    """
    使用PP-Structure进行表格识别
    """

    _ocr_lock = threading.Lock()

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self.table_engine = None
        self._init_ppstructure()

    def _init_ppstructure(self):
        try:
            from paddleocr import PPStructure
            self.table_engine = PPStructure(show_log=False)
        except Exception as e:
            print(f"PP-Structure初始化失败: {e}")
            self.table_engine = None

    def _parse_html_table(self, html_str: str) -> List[List[str]]:
        parser = TableHTMLParser()
        parser.feed(html_str)
        return parser.tables

    def recognize_table(self, image_path: str, is_scanned: bool = False) -> List[List[List[str]]]:
        if not self.table_engine:
            return []
        
        try:
            from PIL import Image
            img = Image.open(image_path).convert('RGB')
            img_np = np.array(img)
            
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            if is_scanned:
                gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
                gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            processed_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            
            with self._ocr_lock:
                result = self.table_engine(processed_img)
            
            if not result:
                return []
            
            tables = []
            for item in result:
                if isinstance(item, dict) and item.get('type') == 'table':
                    res = item.get('res', {})
                    if 'html' in res:
                        html_tables = self._parse_html_table(res['html'])
                        tables.extend(html_tables)
            
            return tables
        except Exception as e:
            print(f"PP-Structure识别失败: {e}")
            import traceback
            traceback.print_exc()
            return []


class PDFTableExtractorPPV3:
    """
    PDF表格提取器 - PP-StructureV3版本
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pp_extractor = PPStructureV3Extractor()
        self._table_cache = {}

    def _is_scanned_pdf(self, page_num: int) -> bool:
        doc = fitz.open(self.pdf_path)
        page = doc.load_page(page_num)
        text = page.get_text()
        blocks = page.get_text("blocks")
        text_block_count = sum(1 for b in blocks if b[6] == 0)
        doc.close()
        if text_block_count < 5 or len(text.strip()) < 20:
            return True
        return False

    def _save_page_image(self, page_num: int) -> str:
        pdf_dir = os.path.dirname(os.path.abspath(self.pdf_path))
        pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        image_dir = os.path.join(pdf_dir, f"{pdf_name}_扫描图片")
        os.makedirs(image_dir, exist_ok=True)
        
        doc = fitz.open(self.pdf_path)
        page = doc.load_page(page_num)
        
        is_scanned = self._is_scanned_pdf(page_num)
        if is_scanned:
            pix = page.get_pixmap(matrix=fitz.Matrix(4.0, 4.0))
        else:
            pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
        
        image_path = os.path.join(image_dir, f"page_{page_num + 1}.png")
        pix.save(image_path)
        doc.close()
        
        return os.path.abspath(image_path)

    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:
        if page_num in self._table_cache:
            return self._table_cache[page_num]
        
        image_path = self._save_page_image(page_num)
        is_scanned = self._is_scanned_pdf(page_num)
        
        tables = self.pp_extractor.recognize_table(image_path, is_scanned)
        self._table_cache[page_num] = tables
        
        return tables

    def extract_all_pages(self) -> Dict[int, List[List[List[str]]]]:
        doc = fitz.open(self.pdf_path)
        total_pages = doc.page_count
        doc.close()
        
        all_tables = {}
        for page_num in range(total_pages):
            tables = self.extract_tables(page_num)
            if tables:
                all_tables[page_num] = tables
        
        return all_tables

    def export_to_excel(self, output_path: str) -> bool:
        try:
            all_tables = self.extract_all_pages()
            
            if not all_tables:
                return False
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                table_index = 0
                for page_num, tables in all_tables.items():
                    for table in tables:
                        df = pd.DataFrame(table)
                        sheet_name = f"表格{table_index + 1}_第{page_num + 1}页"
                        df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                        table_index += 1
            
            return True
        except Exception as e:
            print(f"导出Excel失败: {e}")
            return False


def main():
    import sys
    if len(sys.argv) < 2:
        print("用法: python pdf_table_extractor_ppv3.py <PDF文件路径>")
        return
    
    pdf_path = sys.argv[1]
    extractor = PDFTableExtractorPPV3(pdf_path)
    
    print(f"开始处理: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    doc.close()
    
    print(f"共 {total_pages} 页")
    
    all_tables = extractor.extract_all_pages()
    
    table_count = sum(len(tables) for tables in all_tables.values())
    print(f"识别到 {table_count} 个表格")
    
    if table_count > 0:
        output_path = os.path.splitext(pdf_path)[0] + "_ppv3.xlsx"
        success = extractor.export_to_excel(output_path)
        if success:
            print(f"导出成功: {output_path}")
        else:
            print("导出失败")


if __name__ == "__main__":
    main()
