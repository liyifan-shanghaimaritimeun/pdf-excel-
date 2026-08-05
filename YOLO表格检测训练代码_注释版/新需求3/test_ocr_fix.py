import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_table_extractor import OCRTableExtractor

def test_ocr_with_chinese_path():
    model_dir = r"C:\Users\admin\Desktop\新需求3\测试\models"
    
    print("=" * 70)
    print("OCR中文路径修复测试")
    print("=" * 70)
    print(f"模型目录: {model_dir}")
    print(f"目录存在: {os.path.isdir(model_dir)}")
    print()
    
    print("初始化OCRTableExtractor...")
    extractor = OCRTableExtractor(model_dir=model_dir)
    
    if extractor.ocr:
        print("✓ OCR初始化成功!")
        print(f"OCR对象类型: {type(extractor.ocr)}")
    else:
        print("✗ OCR初始化失败!")

if __name__ == "__main__":
    test_ocr_with_chinese_path()
