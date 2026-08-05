"""
PDF表格提取器 V3 打包脚本
新功能：
  - 型号搜索框（输入特征如 MWIC 全页搜索）
  - 改进坐标聚类（动态Y行阈值、自适应X列检测）
  - 型号统计汇总导出
  - 表内/表外分层OCR识别
"""

import subprocess
import os
import sys
import shutil

# ========== 路径配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = BASE_DIR

# 权重文件路径
weights_dir = os.path.join(BASE_DIR, "..", "weights")
weights_file = os.path.join(weights_dir, "table_1cls_dev.pt")

# 型号库路径
model_db_src = os.path.join(BASE_DIR, "model_db")

# PaddleOCR 模型目录
paddleocr_model_dir = os.path.join(os.path.expanduser("~"), ".paddleocr")
local_models_dir = os.path.join(BASE_DIR, "models")

# 输出名称
EXE_NAME = "PDF表格提取器_v3_最终版"

# ========== 清理旧缓存 ==========
for d in ["build", "dist"]:
    p = os.path.join(BASE_DIR, d)
    if os.path.exists(p):
        shutil.rmtree(p, ignore_errors=True)
    os.makedirs(p, exist_ok=True)

# ========== 构建 PyInstaller 命令 ==========
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile", "--windowed",
    "--name", EXE_NAME,
    "--distpath", "dist",
    "--workpath", "build",
    "--specpath", "build",

    # === 核心业务模块 ===
    "--hidden-import", "openpyxl",
    "--hidden-import", "fitz",
    "--hidden-import", "pdf_table_extractor",

    # === torch + ultralytics (YOLO检测器用) ===
    "--collect-all", "torch",
    "--collect-all", "ultralytics",

    # === PaddlePaddle + PaddleOCR ===
    "--collect-all", "paddle",
    "--collect-all", "paddleocr",
    "--collect-data", "paddleocr",
    "--collect-data", "paddle",
    "--hidden-import", "paddle.fluid",
    "--hidden-import", "paddle.nn",
    "--hidden-import", "paddle.vision",
    "--hidden-import", "paddle.utils.cpp_extension",

    # === 图像/几何依赖 ===
    "--hidden-import", "cv2",
    "--hidden-import", "numpy",
    "--hidden-import", "PIL",
    "--hidden-import", "PIL.Image",
    "--hidden-import", "shapely",
    "--hidden-import", "shapely.geometry",
    "--hidden-import", "pyclipper",
    "--hidden-import", "imgaug",
    "--hidden-import", "lmdb",

    # === GUI ===
    "--hidden-import", "tkinter",
    "--hidden-import", "tkinter.ttk",

    # === 其他 ===
    "--hidden-import", "yaml",
    "--hidden-import", "json",
    "--hidden-import", "csv",
    "--hidden-import", "io",
    "--hidden-import", "re",
    "--hidden-import", "pathlib",
]

# ========== 添加数据文件 ==========
# YOLO 权重
if os.path.exists(weights_file):
    cmd.extend(["--add-data", f"{weights_file};weights"])
    print(f"[OK] YOLO 权重: {weights_file}")
else:
    print(f"[WARN] YOLO 权重不存在: {weights_file}")

# 型号库
if os.path.isdir(model_db_src):
    cmd.extend(["--add-data", f"{model_db_src};model_db"])
    print(f"[OK] 型号库: {model_db_src}")

# 本地 PaddleOCR 模型（优先打包已下载的模型）
local_whl = os.path.join(local_models_dir, "whl")
if os.path.isdir(local_whl):
    cmd.extend(["--add-data", f"{local_whl};models/whl"])
    print(f"[OK] 本地OCR模型: {local_whl}")

# 主入口
cmd.append("pdf_table_gui_v2.py")

# ========== 执行打包 ==========
print(f"\n{'='*60}")
print(f"开始打包: {EXE_NAME}")
print(f"入口文件: pdf_table_gui_v2.py")
print(f"预计耗时: 10-20分钟")
print(f"{'='*60}\n")

result = subprocess.run(cmd, cwd=BASE_DIR)

# ========== 后处理 ==========
if result.returncode == 0:
    print(f"\n[OK] 打包成功！")
    print(f"     EXE: dist\\{EXE_NAME}.exe")

    dist_dir = os.path.join(BASE_DIR, "dist")

    # 1. 复制 YOLO 权重
    dist_weights = os.path.join(dist_dir, "weights")
    if os.path.exists(weights_file):
        os.makedirs(dist_weights, exist_ok=True)
        shutil.copy2(weights_file, os.path.join(dist_weights, "table_1cls_dev.pt"))
        print(f"[OK] YOLO 权重复制完成")

    # 2. 复制型号库
    dist_model_db = os.path.join(dist_dir, "model_db")
    if os.path.isdir(model_db_src):
        if os.path.exists(dist_model_db):
            shutil.rmtree(dist_model_db)
        shutil.copytree(model_db_src, dist_model_db)
        print(f"[OK] 型号库复制完成")

    # 3. 复制 PaddleOCR 模型
    dist_models = os.path.join(dist_dir, "models")
    # 优先使用本地已下载的模型
    if os.path.isdir(local_whl):
        if os.path.exists(dist_models):
            shutil.rmtree(dist_models, ignore_errors=True)
        shutil.copytree(local_models_dir, dist_models)
        print(f"[OK] 本地OCR模型复制完成")
    elif os.path.isdir(paddleocr_model_dir):
        if os.path.exists(dist_models):
            shutil.rmtree(dist_models, ignore_errors=True)
        shutil.copytree(paddleocr_model_dir, dist_models)
        print(f"[OK] 系统OCR模型复制完成")
    else:
        print(f"[WARN] 未找到OCR模型，首次运行将在线下载")

    # 4. 复制使用说明
    readme_src = os.path.join(BASE_DIR, "dist", "使用说明.docx")
    if os.path.exists(readme_src):
        shutil.copy2(readme_src, os.path.join(dist_dir, "使用说明.docx"))

    print(f"\n{'='*60}")
    print(f"全部完成！")
    print(f"输出目录: {dist_dir}")
    print(f"{'='*60}")
else:
    print(f"\n[FAIL] 打包失败！返回码: {result.returncode}")