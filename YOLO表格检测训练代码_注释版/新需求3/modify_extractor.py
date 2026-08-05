import re

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "r", encoding="utf-8") as f:
    content = f.read()

old_method = '''    def _extract_with_ocr(self, page_num: int) -> List[List[List[str]]]:
        """
        使用OCR提取表格

        当PyMuPDF无法识别表格时，使用OCR进行文字识别，然后通过坐标聚类重建表格结构。

        Args:
            page_num: 页码

        Returns:
            表格数据列表
        """
        # 获取OCR识别结果
        cells = self._get_ocr_cells(page_num)

        if not cells:
            return []

        # 按Y坐标聚类，识别行（自适应阈值）
        rows = self._cluster_by_rows(cells)

        if len(rows) < 2:
            return []

        # 检测列位置
        column_x = self._detect_columns(rows)

        if len(column_x) < 2:
            return []

        table = []
        for row in rows:
            row_data = [""] * len(column_x)
            for cell in row:
                min_dist = float('inf')
                min_idx = 0
                for j, x in enumerate(column_x):
                    dist = abs(cell["center_x"] - x)
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = j

                if row_data[min_idx]:
                    row_data[min_idx] += " " + cell["text"]
                else:
                    row_data[min_idx] = cell["text"]
            table.append(row_data)

        split_tables = self.structure_analyzer.split_double_table(table)
        if split_tables and len(split_tables[0]) >= 2:
            return split_tables

        return []'''

new_method = '''    def _save_page_image(self, page_num: int) -> str:
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

    def _extract_with_ocr(self, page_num: int) -> List[List[List[str]]]:
        """
        使用OCR提取表格（优先使用PPStructure）

        提取策略：
        1. 先使用PPStructure专用接口识别表格结构（table=True）
        2. 如果PPStructure未识别到表格，使用传统OCR+坐标聚类方法
        3. 将页面截图保存到与文档同名的文件夹中

        Args:
            page_num: 页码

        Returns:
            表格数据列表
        """
        image_path = self._save_page_image(page_num)

        if self.ocr_extractor and self.ocr_extractor.table_engine:
            tables = self.ocr_extractor.recognize_table_with_ppstructure(image_path)
            if tables:
                all_tables = []
                for table in tables:
                    split_tables = self.structure_analyzer.split_double_table(table)
                    all_tables.extend(split_tables)
                return all_tables

        cells = self._get_ocr_cells(page_num)

        if not cells:
            return []

        rows = self._cluster_by_rows(cells)

        if len(rows) < 2:
            return []

        column_x = self._detect_columns(rows)

        if len(column_x) < 2:
            return []

        table = []
        for row in rows:
            row_data = [""] * len(column_x)
            for cell in row:
                min_dist = float('inf')
                min_idx = 0
                for j, x in enumerate(column_x):
                    dist = abs(cell["center_x"] - x)
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = j

                if row_data[min_idx]:
                    row_data[min_idx] += " " + cell["text"]
                else:
                    row_data[min_idx] = cell["text"]
            table.append(row_data)

        split_tables = self.structure_analyzer.split_double_table(table)
        if split_tables and len(split_tables[0]) >= 2:
            return split_tables

        return []'''

content = content.replace(old_method, new_method)

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "w", encoding="utf-8") as f:
    f.write(content)

print("修改完成")
