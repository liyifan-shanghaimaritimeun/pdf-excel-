import os
import sys
import traceback

def test_ocr_init():
    print("=" * 70)
    print("OCR初始化错误调试")
    print("=" * 70)
    print(f"Python版本: {sys.version}")
    print(f"当前目录: {os.getcwd()}")
    print(f"脚本路径: {sys.argv[0]}")
    print()
    
    try:
        print("1. 尝试导入paddleocr...")
        from paddleocr import PaddleOCR
        print("   ✓ paddleocr导入成功")
        
        print("\n2. 尝试创建PaddleOCR实例...")
        ocr = PaddleOCR(
            lang='ch',
            use_gpu=False,
            use_angle_cls=True,
            show_log=False,
            use_mp=False
        )
        print("   ✓ PaddleOCR创建成功")
        print(f"   OCR实例类型: {type(ocr)}")
        
        print("\n✓ OCR初始化成功!")
        
    except Exception as e:
        print(f"\n✗ OCR初始化失败")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        print("\n   完整堆栈:")
        traceback.print_exc()
        
        print("\n   环境变量:")
        for key in sorted(os.environ.keys()):
            if 'PATH' in key or 'PYTHON' in key or 'PADDLE' in key:
                print(f"     {key}={os.environ[key][:100]}...")

if __name__ == "__main__":
    test_ocr_init()
