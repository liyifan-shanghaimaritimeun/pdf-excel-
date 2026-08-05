with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "r", encoding="utf-8") as f:
    content = f.read()

old_extract = """    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:
        \"\"\"
        提取指定页面的表格数据

        提取策略优化：
        1. 保存页面截图到文件夹
        2. 检测是否为扫描件
        3. 如果是扫描件：优先使用PPStructure识别表格结构，失败则使用传统OCR
        4. 如果是非扫描件：优先使用PyMuPDF快速提取，失败则回退到OCR
        5. 对识别结果进行双栏表格分割处理

        Args:
            page_num: 页码（从0开始）

        Returns:
            表格数据列表，每个表格是一个二维列表
        \"\"\"
        self._save_page_image(page_num)
        
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

new_extract = """    def _is_valid_table(self, table: List[List[str]]) -> bool:
        if not table or len(table) < 2:
            return False
        col_count = len(table[0])
        if col_count < 2:
            return False
        valid_cols = 0
        for row in table[:5]:
            if len(row) >= col_count:
                non_empty = sum(1 for cell in row if cell and str(cell).strip())
                if non_empty >= 2:
                    valid_cols += 1
        return valid_cols >= 2

    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:
        \"\"\"
        提取指定页面的表格数据

        提取策略：
        1. 保存页面截图到文件夹
        2. 检测是否为扫描件
        3. 非扫描件：优先使用PyMuPDF，失败再OCR
        4. 扫描件：优先使用OCR，失败再PPStructure
        5. 验证表格有效性后输出

        Args:
            page_num: 页码（从0开始）

        Returns:
            表格数据列表，每个表格是一个二维列表
        \"\"\"
        self._save_page_image(page_num)
        
        is_scanned = self._is_scanned_pdf(page_num)
        
        if not is_scanned:
            tables = self._extract_with_pymupdf(page_num)
            
            all_tables = []
            for table in tables:
                split_tables = self.structure_analyzer.split_double_table(table)
                for t in split_tables:
                    if self._is_valid_table(t):
                        all_tables.append(t)
            
            if all_tables:
                return all_tables
            
            if self.use_ocr:
                self._init_ocr_if_needed()
                if self.ocr_extractor:
                    tables = self._extract_with_ocr(page_num)
                    valid_tables = [t for t in tables if self._is_valid_table(t)]
                    if valid_tables:
                        return valid_tables
            
            return []
        else:
            if self.use_ocr:
                self._init_ocr_if_needed()
                if self.ocr_extractor:
                    tables = self._extract_with_ocr(page_num)
                    valid_tables = [t for t in tables if self._is_valid_table(t)]
                    if valid_tables:
                        return valid_tables
                    
                    image_path = os.path.join(
                        os.path.dirname(self.pdf_path),
                        f"{os.path.splitext(os.path.basename(self.pdf_path))[0]}_扫描图片",
                        f"page_{page_num + 1}.png"
                    )
                    tables = self.ocr_extractor.recognize_table_with_ppstructure(image_path)
                    valid_tables = [t for t in tables if isinstance(t, list) and self._is_valid_table(t)]
                    if valid_tables:
                        return valid_tables
            
            return []"""

content = content.replace(old_extract, new_extract)

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK")
