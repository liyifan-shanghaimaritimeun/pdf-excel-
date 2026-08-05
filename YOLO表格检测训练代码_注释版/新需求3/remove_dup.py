with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

result = []
skip = False
skip_count = 0

for line in lines:
    if skip:
        skip_count += 1
        if skip_count >= 10:
            skip = False
            skip_count = 0
        else:
            continue
    if "def _is_scanned_pdf(self, page_num: int) -> bool:" in line and result and "def _is_scanned_pdf" in "".join(result[-20:]):
        skip = True
        continue
    result.append(line)

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "w", encoding="utf-8") as f:
    f.writelines(result)

print("OK")
