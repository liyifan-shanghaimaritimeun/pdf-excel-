with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

result = []
skip_next = False

for line in lines:
    if skip_next:
        skip_next = False
        continue
    if "        return all_tables" in line:
        result.append(line)
        skip_next = True
        continue
    result.append(line)

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor_v1.py", "w", encoding="utf-8") as f:
    f.writelines(result)

print("OK")
