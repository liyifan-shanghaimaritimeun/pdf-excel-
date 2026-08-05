import os
import shutil
import glob
from paddleocr import PaddleOCR

def copy_models_to_english_path():
    source_base = r"C:\Users\admin\Desktop\新需求3\测试\models"
    dest_base = r"C:\Users\admin\Desktop\newreq3\models"
    
    if os.path.exists(dest_base):
        shutil.rmtree(dest_base)
    
    shutil.copytree(source_base, dest_base)
    print(f"模型已复制到: {dest_base}")
    return dest_base

def test_with_english_path(model_dir):
    print(f"\n使用英文路径测试: {model_dir}")
    
    det_pattern = os.path.join(model_dir, '**', '*_det_infer', 'inference.pdmodel')
    rec_pattern = os.path.join(model_dir, '**', '*_rec_infer', 'inference.pdmodel')
    cls_pattern = os.path.join(model_dir, '**', '*_cls_infer', 'inference.pdmodel')
    
    det_models = glob.glob(det_pattern, recursive=True)
    rec_models = glob.glob(rec_pattern, recursive=True)
    cls_models = glob.glob(cls_pattern, recursive=True)
    
    print(f"det_models: {det_models}")
    print(f"rec_models: {rec_models}")
    print(f"cls_models: {cls_models}")
    
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
    model_dir = copy_models_to_english_path()
    test_with_english_path(model_dir)
