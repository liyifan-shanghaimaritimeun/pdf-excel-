import re

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "r", encoding="utf-8") as f:
    content = f.read()

insert_point = content.find("def _preprocess_image")
if insert_point != -1:
    new_method = """    def recognize_table_with_ppstructure(self, image_path: str) -> List[List[List[str]]]:
        \"\"\"
        使用PPStructure专用接口识别表格结构（table=True）
        
        Args:
            image_path: 图片文件路径
        
        Returns:
            表格数据列表，每个表格是一个二维列表
        \"\"\"
        if not self.table_engine:
            return []
        
        try:
            with self._ocr_lock:
                result = self.table_engine(image_path)
                
            tables = []
            for item in result:
                if item["type"] == "table":
                    table_data = []
                    if "res" in item:
                        for row in item["res"]:
                            row_data = [str(cell).strip() if cell else "" for cell in row]
                            table_data.append(row_data)
                    if table_data and len(table_data) >= 2 and len(table_data[0]) >= 2:
                        tables.append(table_data)
            
            return tables
        except Exception:
            return []

"""
    content = content[:insert_point] + new_method + content[insert_point:]

with open(r"c:\Users\admin\Desktop\新需求3\pdf_table_extractor.py", "w", encoding="utf-8") as f:
    f.write(content)

print("PPStructure方法已添加")
