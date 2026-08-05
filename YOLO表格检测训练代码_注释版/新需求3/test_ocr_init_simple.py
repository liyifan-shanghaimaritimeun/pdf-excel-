import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("OCR初始化简单测试")
print("=" * 70)

model_dir = r"C:\Users\admin\Desktop\新需求3\测试\models"
print(f"模型目录: {model_dir}")
print(f"目录存在: {os.path.isdir(model_dir)}")
print()

try:
    print("尝试导入OCRTableExtractor...")
    from pdf_table_extractor import OCRTableExtractor
    print("✓ 导入成功")
    
    print("\n创建OCRTableExtractor...")
    extractor = OCRTableExtractor(model_dir=model_dir)
    print("✓ 创建成功")
    
    if extractor.ocr:
        print("✓ OCR初始化成功")
    else:
        print("✗ OCR未初始化")
        
except Exception as e:
    print(f"✗ 出错: {e}")
    print("\n完整堆栈:")
    traceback.print_exc()
