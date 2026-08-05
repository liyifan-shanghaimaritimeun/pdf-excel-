"""
测试 PPStructure 专用接口
"""
import sys, os, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz

# 测试1: 尝试 PP-Structure 专用类
print("=== 测试1: PPStructure 类 ===")
try:
    import paddleocr
    # 检查是否有 PPStructure
    if hasattr(paddleocr, 'PPStructure'):
        print("paddleocr.PPStructure 存在")
    else:
        print("paddleocr.PPStructure 不存在")
    # 列出 paddleocr 的所有属性
    attrs = [a for a in dir(paddleocr) if not a.startswith('_') and 'struct' in a.lower()]
    print(f"包含'struct'的属性: {attrs}")
except Exception as e:
    print(f"异常: {e}")

# 测试2: 尝试其他类名
print("\n=== 测试2: 尝试其他类 ===")
try:
    from paddleocr import PPStructure
    print("PPStructure 可以导入")
except ImportError as e:
    print(f"PPStructure 导入失败: {e}")
except SyntaxError as e:
    print(f"语法错误: {e}")

# 测试3: 检查 paddleocr 版本和可用属性
print("\n=== 测试3: 检查版本和API ===")
import paddleocr
print(f"版本: {paddleocr.__version__}")

# 测试4: 检查 PaddleOCR 是否有 predict 方法
print("\n=== 测试4: PaddleOCR 方法 ===")
from paddleocr import PaddleOCR
ocr = PaddleOCR(lang='ch', use_angle_cls=True, show_log=False, table=True)

# 检查可用方法
methods = [m for m in dir(ocr) if not m.startswith('_')]
print(f"公开方法: {methods}")

# 测试 predict 方法
if hasattr(ocr, 'predict'):
    print("\n=== 测试 predict ===")
    pdf_path = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\磁稳产品手册(2025版).pdf'
    doc = fitz.open(pdf_path)
    page_num = 6
    page = doc.load_page(page_num)
    dpi = 300
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
    temp_path = "test_page.png"
    pix.save(temp_path)
    
    try:
        result = ocr.predict(temp_path)
        print(f"predict 返回类型: {type(result)}")
        if result:
            print(f"predict 返回长度: {len(result)}")
            if isinstance(result, list) and len(result) > 0:
                item = result[0]
                print(f"第一个元素类型: {type(item)}")
                if isinstance(item, dict):
                    print(f"第一个元素键: {list(item.keys())}")
                elif isinstance(item, list):
                    print(f"第一个元素长度: {len(item)}")
    except Exception as e:
        print(f"predict 异常: {e}")
    
    doc.close()
    os.remove(temp_path)

# 测试5: 尝试直接用ocr.predict with table=True
print("\n=== 测试5: 直接调用ocr.predict ===")
try:
    import paddle
    print(f"PaddlePaddle版本: {paddle.__version__}")
except:
    print("无法获取PaddlePaddle版本")
