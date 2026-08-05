import os
import sys
import glob

def test_model_path():
    print("=" * 70)
    print("模型路径查找测试")
    print("=" * 70)
    
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    print(f"程序目录: {exe_dir}")
    print(f"是否打包: {getattr(sys, 'frozen', False)}")
    print()
    
    models_dir = os.path.join(exe_dir, 'models')
    print(f"models目录: {models_dir}")
    print(f"models目录存在: {os.path.isdir(models_dir)}")
    
    if os.path.isdir(models_dir):
        det_pattern = os.path.join(models_dir, '**', '*_det_infer', 'inference.pdmodel')
        rec_pattern = os.path.join(models_dir, '**', '*_rec_infer', 'inference.pdmodel')
        cls_pattern = os.path.join(models_dir, '**', '*_cls_infer', 'inference.pdmodel')
        
        print(f"\n查找模型文件:")
        print(f"  det_pattern: {det_pattern}")
        print(f"  rec_pattern: {rec_pattern}")
        print(f"  cls_pattern: {cls_pattern}")
        
        det_models = glob.glob(det_pattern, recursive=True)
        rec_models = glob.glob(rec_pattern, recursive=True)
        cls_models = glob.glob(cls_pattern, recursive=True)
        
        print(f"\n找到的模型:")
        print(f"  det: {det_models}")
        print(f"  rec: {rec_models}")
        print(f"  cls: {cls_models}")
        
        if det_models and rec_models:
            print("\n✓ 模型路径查找成功!")
            return models_dir
        else:
            print("\n✗ 模型路径查找失败!")
            return None
    else:
        print("\n✗ models目录不存在!")
        return None

def test_ocr_init(model_dir):
    print("\n" + "=" * 70)
    print("OCR初始化测试")
    print("=" * 70)
    
    try:
        from paddleocr import PaddleOCR
        
        ocr_kwargs = {
            'lang': 'ch',
            'use_gpu': False,
            'use_angle_cls': True,
            'show_log': False
        }
        
        if model_dir:
            det_pattern = os.path.join(model_dir, '**', '*_det_infer', 'inference.pdmodel')
            rec_pattern = os.path.join(model_dir, '**', '*_rec_infer', 'inference.pdmodel')
            cls_pattern = os.path.join(model_dir, '**', '*_cls_infer', 'inference.pdmodel')
            
            det_models = glob.glob(det_pattern, recursive=True)
            rec_models = glob.glob(rec_pattern, recursive=True)
            cls_models = glob.glob(cls_pattern, recursive=True)
            
            if det_models:
                det_model_dir = os.path.dirname(det_models[0])
                det_model_dir = det_model_dir.replace('\\', '/')
                ocr_kwargs['det_model_dir'] = det_model_dir
                print(f"det_model_dir: {ocr_kwargs['det_model_dir']}")
            if rec_models:
                rec_model_dir = os.path.dirname(rec_models[0])
                rec_model_dir = rec_model_dir.replace('\\', '/')
                ocr_kwargs['rec_model_dir'] = rec_model_dir
                print(f"rec_model_dir: {ocr_kwargs['rec_model_dir']}")
            if cls_models:
                cls_model_dir = os.path.dirname(cls_models[0])
                cls_model_dir = cls_model_dir.replace('\\', '/')
                ocr_kwargs['cls_model_dir'] = cls_model_dir
                print(f"cls_model_dir: {ocr_kwargs['cls_model_dir']}")
        
        print("\n初始化PaddleOCR...")
        ocr = PaddleOCR(**ocr_kwargs)
        print("✓ OCR初始化成功!")
        return ocr
    except Exception as e:
        print(f"✗ OCR初始化失败: {e}")
        return None

if __name__ == "__main__":
    model_dir = test_model_path()
    ocr = test_ocr_init(model_dir)
    
    if ocr:
        print("\n✓ 所有测试通过!")
    else:
        print("\n✗ 测试失败!")
