with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "r", encoding="utf-8") as f:
    content = f.read()

method = """    def _is_scanned_pdf(self, page_num: int) -> bool:
        doc = fitz.open(self.pdf_path)
        page = doc.load_page(page_num)
        text = page.get_text()
        blocks = page.get_text("blocks")
        text_block_count = sum(1 for b in blocks if b[6] == 0)
        doc.close()
        if text_block_count < 5 or len(text.strip()) < 20:
            return True
        return False

"""

content = content.replace('    def _save_page_image(self, page_num: int) -> str:', method + '    def _save_page_image(self, page_num: int) -> str:')

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "w", encoding="utf-8") as f:
    f.write(content)

print("OK")
