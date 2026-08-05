import re

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "r", encoding="utf-8") as f:
    content = f.read()

save_method = '''    def _save_page_image(self, page_num: int) -> str:
        import os
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

'''

content = content.replace('    def extract_tables(self, page_num: int = 0)', save_method + '    def extract_tables(self, page_num: int = 0)')

content = content.replace('        # 第一层：PyMuPDF快速提取', '        self._save_page_image(page_num)\n        \n        # 第一层：PyMuPDF快速提取')

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK")
