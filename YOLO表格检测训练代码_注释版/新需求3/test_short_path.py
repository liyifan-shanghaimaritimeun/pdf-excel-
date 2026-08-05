import os
import ctypes

def get_short_path_name(long_path):
    """获取Windows短路径名（8.3格式）"""
    try:
        if not os.path.exists(long_path):
            return long_path
        
        buf = ctypes.create_unicode_buffer(260)
        ctypes.windll.kernel32.GetShortPathNameW(long_path, buf, 260)
        return buf.value
    except:
        return long_path

def test_with_short_path():
    from paddleocr import PaddleOCR
    
    base_path = r"C:\Users\admin\Desktop\新需求3\测试\models"
    
    short_base = get_short_path_name(base_path)
    print(f"长路径: {base_path}")
    print(f"短路径: {short_base}")
    print()
    
    import glob
    det_pattern = os.path.join(short_base, '**', '*_det_infer', 'inference.pdmodel')
    rec_pattern = os.path.join(short_base, '**', '*_rec_infer', 'inference.pdmodel')
    cls_pattern = os.path.join(short_base, '**', '*_cls_infer', 'inference.pdmodel')
    
    det_models = glob.glob(det_pattern, recursive=True)
    rec_models = glob.glob(rec_pattern, recursive=True)
    cls_models = glob.glob(cls_pattern, recursive=True)
    
    print(f"det_models: {det_models}")
    print(f"rec_models: {rec_models}")
    print(f"cls_models: {cls_models}")
    print()
    
    ocr_kwargs = {
        'lang': 'ch',
        'use_gpu': False,
        'use_angle_cls': True,
        'show_log': False
    }
    
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
    try:
        ocr = PaddleOCR(**ocr_kwargs)
        print("✓ OCR初始化成功!")
        return ocr
    except Exception as e:
        print(f"✗ OCR初始化失败: {e}")
        return None

if __name__ == "__main__":
    test_with_short_path()
