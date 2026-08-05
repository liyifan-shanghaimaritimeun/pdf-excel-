import re

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
            result.append('    def _save_page_image(self, page_num: int) -> str:\n')
            result.append('        pdf_dir = os.path.dirname(self.pdf_path)\n')
            result.append('        pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]\n')
            result.append('        image_dir = os.path.join(pdf_dir, f"{pdf_name}_扫描图片")\n')
            result.append('        os.makedirs(image_dir, exist_ok=True)\n')
            result.append('        doc = fitz.open(self.pdf_path)\n')
            result.append('        page = doc.load_page(page_num)\n')
            result.append('        is_scanned = self._is_scanned_pdf(page_num)\n')
            result.append('        if is_scanned:\n')
            result.append('            pix = page.get_pixmap(matrix=fitz.Matrix(4.0, 4.0))\n')
            result.append('        else:\n')
            result.append('            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))\n')
            result.append('        image_path = os.path.join(image_dir, f"page_{page_num + 1}.png")\n')
            result.append('        pix.save(image_path)\n')
            result.append('        doc.close()\n')
            result.append('        return image_path\n')
            result.append('\n')
            result.append('    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:\n')
            result.append('        self._save_page_image(page_num)\n')
            result.append('        if self.use_ocr:\n')
            result.append('            tables = self._extract_with_ocr(page_num)\n')
            result.append('            if tables:\n')
            result.append('                return tables\n')
            result.append('        tables = self._extract_with_pymupdf(page_num)\n')
            result.append('        all_tables = []\n')
            result.append('        for table in tables:\n')
            result.append('            split_tables = self.structure_analyzer.split_double_table(table)\n')
            result.append('            all_tables.extend(split_tables)\n')
            result.append('        return all_tables\n')

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "w", encoding="utf-8") as f:
    f.writelines(result)

print("修改完成")
