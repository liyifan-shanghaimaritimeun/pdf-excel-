with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

result = []
in_method = False
method_lines = []

for line in lines:
    if not in_method:
        if "def extract_tables(self, page_num" in line:
            in_method = True
            method_lines.append(line)
        else:
            result.append(line)
    else:
        method_lines.append(line)
        if line.strip() == "return []":
            in_method = False
            result.append('    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:\n')
            result.append('        """\n')
            result.append('        提取指定页面的表格数据\n')
            result.append('\n')
            result.append('        提取策略优化：\n')
            result.append('        1. 保存页面截图到文件夹\n')
            result.append('        2. 检测是否为扫描件\n')
            result.append('        3. 如果是扫描件：优先使用PPStructure识别表格结构，失败则使用传统OCR\n')
            result.append('        4. 如果是非扫描件：优先使用PyMuPDF快速提取，失败则回退到OCR\n')
            result.append('        5. 对识别结果进行双栏表格分割处理\n')
            result.append('\n')
            result.append('        Args:\n')
            result.append('            page_num: 页码（从0开始）\n')
            result.append('\n')
            result.append('        Returns:\n')
            result.append('            表格数据列表，每个表格是一个二维列表\n')
            result.append('        """\n')
            result.append('        self._save_page_image(page_num)\n')
            result.append('\n')
            result.append('        is_scanned = self._is_scanned_pdf(page_num)\n')
            result.append('\n')
            result.append('        if is_scanned and self.use_ocr:\n')
            result.append('            self._init_ocr_if_needed()\n')
            result.append('            if self.ocr_extractor:\n')
            result.append('                image_path = os.path.join(\n')
            result.append('                    os.path.dirname(self.pdf_path),\n')
            result.append('                    f"{os.path.splitext(os.path.basename(self.pdf_path))[0]}_扫描图片",\n')
            result.append('                    f"page_{page_num + 1}.png"\n')
            result.append('                )\n')
            result.append('                tables = self.ocr_extractor.recognize_table_with_ppstructure(image_path)\n')
            result.append('                if tables:\n')
            result.append('                    return tables\n')
            result.append('\n')
            result.append('                tables = self._extract_with_ocr(page_num)\n')
            result.append('                if tables:\n')
            result.append('                    return tables\n')
            result.append('\n')
            result.append('            return []\n')
            result.append('\n')
            result.append('        tables = self._extract_with_pymupdf(page_num)\n')
            result.append('\n')
            result.append('        all_tables = []\n')
            result.append('        for table in tables:\n')
            result.append('            split_tables = self.structure_analyzer.split_double_table(table)\n')
            result.append('            all_tables.extend(split_tables)\n')
            result.append('\n')
            result.append('        if all_tables:\n')
            result.append('            return all_tables\n')
            result.append('\n')
            result.append('        if self.use_ocr:\n')
            result.append('            tables = self._extract_with_ocr(page_num)\n')
            result.append('            if tables:\n')
            result.append('                return tables\n')
            result.append('\n')
            result.append('        return []\n')

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "w", encoding="utf-8") as f:
    f.writelines(result)

print("修改完成")
