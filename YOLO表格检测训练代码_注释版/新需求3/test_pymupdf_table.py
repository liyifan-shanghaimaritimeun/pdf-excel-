import fitz

pdf_path = '最新目录PDF/AJ.pdf'
doc = fitz.open(pdf_path)
page = doc.load_page(0)

tabs = page.find_tables()
tables = tabs.tables
print(f"找到 {len(tables)} 个表格")

for i, tab in enumerate(tables):
    print(f"\n=== 表格 {i} ===")
    print(f"位置: {tab.bbox}")
    
    data = tab.extract()
    print(f"行数: {len(data)}, 列数: {len(data[0]) if data else 0}")
    
    for j, row in enumerate(data):
        print(f"  行{j}: {row}")