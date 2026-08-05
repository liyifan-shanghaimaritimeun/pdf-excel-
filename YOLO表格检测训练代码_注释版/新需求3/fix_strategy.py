with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "r", encoding="utf-8") as f:
    content = f.read()

old_strategy = """        self._save_page_image(page_num)
        
        # 第一层：PyMuPDF快速提取
        tables = self._extract_with_pymupdf(page_num)"""

new_strategy = """        self._save_page_image(page_num)
        
        is_scanned = self._is_scanned_pdf(page_num)
        
        if is_scanned and self.use_ocr:
            self._init_ocr_if_needed()
            if self.ocr_extractor:
                image_path = os.path.join(os.path.dirname(self.pdf_path), f"{os.path.splitext(os.path.basename(self.pdf_path))[0]}_扫描图片", f"page_{page_num + 1}.png")
                tables = self.ocr_extractor.recognize_table_with_ppstructure(image_path)
                if tables:
                    return tables
                tables = self._extract_with_ocr(page_num)
                if tables:
                    return tables
            return []
        
        # 第一层：PyMuPDF快速提取
        tables = self._extract_with_pymupdf(page_num)"""

content = content.replace(old_strategy, new_strategy)

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK")
