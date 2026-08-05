with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "r", encoding="utf-8") as f:
    content = f.read()

old_strategy = """        self._save_page_image(page_num)
        
        is_scanned = self._is_scanned_pdf(page_num)
        
        if is_scanned and self.use_ocr:
            self._init_ocr_if_needed()
            if self.ocr_extractor:
                image_path = os.path.join(
                    os.path.dirname(self.pdf_path),
                    f"{os.path.splitext(os.path.basename(self.pdf_path))[0]}_扫描图片",
                    f"page_{page_num + 1}.png"
                )
                tables = self.ocr_extractor.recognize_table_with_ppstructure(image_path)
                if tables:
                    return tables
                
                tables = self._extract_with_ocr(page_num)
                if tables:
                    return tables
            
            return []
        
        tables = self._extract_with_pymupdf(page_num)

        all_tables = []
        for table in tables:
            split_tables = self.structure_analyzer.split_double_table(table)
            all_tables.extend(split_tables)

        if all_tables:
            return all_tables

        if self.use_ocr:
            tables = self._extract_with_ocr(page_num)
            if tables:
                return tables"""

new_strategy = """        self._save_page_image(page_num)
        
        if self.use_ocr:
            self._init_ocr_if_needed()
            if self.ocr_extractor:
                tables = self._extract_with_ocr(page_num)
                if tables:
                    return tables
        
        tables = self._extract_with_pymupdf(page_num)

        all_tables = []
        for table in tables:
            split_tables = self.structure_analyzer.split_double_table(table)
            all_tables.extend(split_tables)

        return all_tables"""

content = content.replace(old_strategy, new_strategy)

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK")
