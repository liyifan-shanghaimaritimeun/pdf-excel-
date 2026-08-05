import re

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "r", encoding="utf-8") as f:
    content = f.read()

old_method = '''    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:
        """
        提取指定页面的表格数据

        提取策略：
        1. 强制使用OCR识别（确保扫描件能被正确识别）
        2. 如果OCR未启用或失败，再尝试PyMuPDF作为备用
        3. 对识别结果进行双栏表格分割处理

        Args:
            page_num: 页码（从0开始）

        Returns:
            表格数据列表，每个表格是一个二维列表
        """
        if self.use_ocr:
            tables = self._extract_with_ocr(page_num)
            if tables:
                return tables

        tables = self._extract_with_pymupdf(page_num)

        all_tables = []
        for table in tables:
            if self._is_pymupdf_result_valid(table):
                split_tables = self.structure_analyzer.split_double_table(table)
                all_tables.extend(split_tables)

        return all_tables'''

new_method = '''    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:
        """
        提取指定页面的表格数据

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
            if self._is_pymupdf_result_valid(table):
                split_tables = self.structure_analyzer.split_double_table(table)
                all_tables.extend(split_tables)

        return all_tables'''

content = content.replace(old_method, new_method)

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成")
