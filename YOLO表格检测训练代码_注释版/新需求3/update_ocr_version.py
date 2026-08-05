import re

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "r", encoding="utf-8") as f:
    content = f.read()

old_extract = '''    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:
        """
        提取指定页面的表格数据

        提取策略：
        1. 优先使用PyMuPDF的find_tables()方法（速度快，毫秒级）
        2. 如果PyMuPDF未找到表格，使用OCR识别（速度较慢，秒级）
        3. 对识别结果进行双栏表格分割处理

        Args:
            page_num: 页码（从0开始）

        Returns:
            表格数据列表，每个表格是一个二维列表
        """
        # 第一层：PyMuPDF快速提取
        tables = self._extract_with_pymupdf(page_num)

        all_tables = []
        for table in tables:
            # 检测并分割双栏表格
            # split_double_table内部已包含清洗逻辑：
            # - 如果是双栏表格，分割后对每个子表格独立清洗
            # - 如果不是双栏表格，直接清洗后返回
            split_tables = self.structure_analyzer.split_double_table(table)
            all_tables.extend(split_tables)

        # 如果PyMuPDF提取到表格，直接返回
        if all_tables:
            return all_tables

        # 第二层：OCR回退提取
        if self.use_ocr:
            tables = self._extract_with_ocr(page_num)
            if tables:
                return tables

        return []'''

new_extract = '''    def _save_page_image(self, page_num: int) -> str:
        """
        将PDF页面保存为图片到同名文件夹
        
        Args:
            page_num: 页码
        
        Returns:
            保存的图片路径
        """
        pdf_dir = os.path.dirname(self.pdf_path)
        pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        image_dir = os.path.join(pdf_dir, f"{pdf_name}_扫描图片")
        os.makedirs(image_dir, exist_ok=True)
        
        doc = fitz.open(self.pdf_path)
        page = doc.load_page(page_num)
        
        is_scanned = self._is_scanned_pdf(page_num)
        if is_scanned:
            pix = page.get_pixmap(matrix=fitz.Matrix(4.0, 4.0))
        else:
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        
        image_path = os.path.join(image_dir, f"page_{page_num + 1}.png")
        pix.save(image_path)
        doc.close()
        
        return image_path

    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:
        """
        提取指定页面的表格数据（强制OCR版本）

        提取策略：
        1. 保存页面截图到文件夹
        2. 强制使用OCR识别（确保扫描件能被正确识别）
        3. 如果OCR未启用或失败，再尝试PyMuPDF作为备用
        4. 对识别结果进行双栏表格分割处理

        Args:
            page_num: 页码（从0开始）

        Returns:
            表格数据列表，每个表格是一个二维列表
        """
        self._save_page_image(page_num)

        if self.use_ocr:
            tables = self._extract_with_ocr(page_num)
            if tables:
                return tables

        tables = self._extract_with_pymupdf(page_num)

        all_tables = []
        for table in tables:
            split_tables = self.structure_analyzer.split_double_table(table)
            all_tables.extend(split_tables)

        return all_tables'''

content = content.replace(old_extract, new_extract)

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成")
