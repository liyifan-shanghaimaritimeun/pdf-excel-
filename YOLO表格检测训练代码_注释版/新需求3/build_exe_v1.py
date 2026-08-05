import os
import subprocess
import sys

def build_exe():
    script_path = "pdf_table_gui.py"
    output_dir = "dist"
    
    add_data_params = []
    
    paddleocr_dir = os.path.join(sys.prefix, "Lib", "site-packages", "paddleocr")
    if os.path.exists(paddleocr_dir):
        add_data_params.append(f"--add-data={paddleocr_dir};paddleocr")
    
    ppocr_dir = os.path.join(sys.prefix, "Lib", "site-packages", "ppocr")
    if os.path.exists(ppocr_dir):
        add_data_params.append(f"--add-data={ppocr_dir};ppocr")
    
    cmd = [
        "python", "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "PDF表格提取器",
        "--distpath", output_dir,
        "--workpath", "build",
        "--specpath", "build",
        script_path
    ]
    cmd.extend(add_data_params)
    
    print(f"执行命令: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
    
    print("\n=== 标准输出 ===")
    print(result.stdout)
    
    if result.stderr:
        print("\n=== 错误输出 ===")
        print(result.stderr)
    
    print(f"\n返回码: {result.returncode}")
    
    if result.returncode == 0:
        exe_path = os.path.join(output_dir, "PDF表格提取器.exe")
        if os.path.exists(exe_path):
            print(f"\n✓ 打包成功！EXE文件位于: {exe_path}")
        else:
            print("\n✗ 打包命令成功，但未找到EXE文件")
    else:
        print("\n✗ 打包失败")

if __name__ == "__main__":
    build_exe()