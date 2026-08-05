import subprocess
import os
import sys
import shutil

os.makedirs("dist", exist_ok=True)
os.makedirs("build", exist_ok=True)

# 权重文件路径
weights_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "weights")
weights_file = os.path.join(weights_dir, "table_1cls_dev.pt")

# 清理旧的 build 缓存
if os.path.exists("build"):
    shutil.rmtree("build", ignore_errors=True)
os.makedirs("build", exist_ok=True)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onefile", "--windowed",
    "--name", "PDF表格提取器_v2_最终版",
    "--distpath", "dist",
    "--workpath", "build",
    "--specpath", "build",
    # === 核心业务 ===
    "--hidden-import", "openpyxl",
    "--hidden-import", "fitz",
    "--hidden-import", "pdf_table_extractor",
    # === torch: 用 --collect-all 跳过 DLL 依赖分析循环 ===
    "--collect-all", "torch",
    # === ultralytics: 同理 ===
    "--collect-all", "ultralytics",
    # === PaddleOCR: 精确收集子模块 + 数据 ===
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

# 权重文件打包
if os.path.exists(weights_file):
    cmd.extend(["--add-data", f"{weights_file};weights"])
    print(f"已添加权重文件: {weights_file}")
else:
    print(f"权重文件不存在: {weights_file}")

# 型号库打包
model_db_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_db")
if os.path.isdir(model_db_src):
    cmd.extend(["--add-data", f"{model_db_src};model_db"])
    print(f"已添加型号库: {model_db_src}")

cmd.append("pdf_table_gui_v2.py")

print("开始打包 (collect-all torch + ultralytics)...")
print("预计耗时: 10-20分钟")
result = subprocess.run(cmd)

if result.returncode == 0:
    print("\n打包成功！EXE: dist\\PDF表格提取器_v2_最终版.exe")

    # 复制权重文件到dist
    dist_weights_dir = os.path.join("dist", "weights")
    if os.path.exists(weights_file):
        os.makedirs(dist_weights_dir, exist_ok=True)
        shutil.copy2(weights_file, os.path.join(dist_weights_dir, "table_1cls_dev.pt"))
        print(f"权重已复制到: {dist_weights_dir}")

    # 复制型号库
    dist_model_db_dir = os.path.join("dist", "model_db")
    if os.path.isdir(model_db_src):
        if os.path.exists(dist_model_db_dir):
            shutil.rmtree(dist_model_db_dir)
        shutil.copytree(model_db_src, dist_model_db_dir)
        print(f"型号库已复制到: {dist_model_db_dir}")

    # 复制PaddleOCR模型
    user_home = os.path.expanduser("~")
    paddleocr_model_dir = os.path.join(user_home, ".paddleocr")
    dist_model_dir = os.path.join("dist", "models")
    if os.path.isdir(paddleocr_model_dir):
        print("复制PaddleOCR模型...")
        if os.path.exists(dist_model_dir):
            shutil.rmtree(dist_model_dir)
        shutil.copytree(paddleocr_model_dir, dist_model_dir)
        print(f"OCR模型已复制到: {dist_model_dir}")

    print("\n全部完成！")
else:
    print("\n打包失败！返回码:", result.returncode)
