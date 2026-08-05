"""
测试 PPStructureV3 正确参数 (不传options)
"""
import sys, os, json, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fitz
from paddleocr import PPStructureV3

print(f"版本: {__import__('paddleocr').__version__}")

# 尝试不带options
print("\n=== 初始化 PPStructureV3 ===")
try:
    pp = PPStructureV3(use_table_recognition=True)
    print("初始化成功(use_table_recognition=True)")
except Exception as e:
    print(f"use_table_recognition=True 失败: {str(e)[:100]}")
    try:
        pp = PPStructureV3()
        print("默认初始化成功")
    except Exception as e2:
        print(f"默认初始化也失败: {str(e2)[:100]}")
        
        # 检查PaddlePaddle版本
        try:
            import paddle
            print(f"PaddlePaddle版本: {paddle.__version__}")
        except:
            print("无法获取PaddlePaddle版本")
        
        # 尝试降级方案：用 PaddleOCR + table=True
        print("\n=== 降级方案: PaddleOCR(table=True) ===")
        from paddleocr import PaddleOCR
        try:
            ocr_table = PaddleOCR(
                lang='ch',
                use_angle_cls=True,
                show_log=False,
                table=True
            )
            print("PaddleOCR(table=True) 初始化成功!")
            
            # 测试
            pdf_path = r'C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列\磁稳产品手册(2025版).pdf'
            doc = fitz.open(pdf_path)
            page_num = 6
            page = doc.load_page(page_num)
            dpi = 300
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72.0, dpi / 72.0))
            temp_path = "test_page.png"
            pix.save(temp_path)
            
            result = ocr_table.ocr(temp_path, cls=True)
            print(f"\nPaddleOCR(table=True) 返回:")
            if result and result[0]:
                print(f"  结果数量: {len(result[0])}")
                for i, item in enumerate(result[0][:5]):
                    if isinstance(item, dict):
                        keys = list(item.keys())
                        print(f"  [{i}] dict: keys={keys}")
                        for k in keys:
                            v = item[k]
                            if k == 'table':
                                print(f"      table: {type(v).__name__}, len={len(v) if isinstance(v, (list,str)) else 'N/A'}")
                                if isinstance(v, str):
                                    print(f"        内容前200: {v[:200]}")
                                elif isinstance(v, list):
                                    print(f"        行数: {len(v)}")
                                    if len(v) > 0:
                                        print(f"        第一行: {v[0]}")
                    elif isinstance(item, list):
                        print(f"  [{i}] list: bbox={item[0] if len(item)>0 else 'N/A'}")
            
            os.remove(temp_path)
            doc.close()
        except Exception as e3:
            print(f"PaddleOCR(table=True) 也失败: {e3}")
            import traceback
            traceback.print_exc()
