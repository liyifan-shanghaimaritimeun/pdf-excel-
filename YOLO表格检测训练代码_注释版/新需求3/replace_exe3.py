import os
import shutil
import subprocess

old_path = r"C:\Users\admin\Desktop\新需求3\测试\PDF表格提取器.exe"
new_path = r"C:\Users\admin\Desktop\新需求3\测试\dist\PDF表格提取器.exe"

try:
    subprocess.run(["taskkill", "/f", "/im", "PDF表格提取器.exe"], capture_output=True)
    os.system("timeout /t 2 /nobreak >nul")
    
    if os.path.exists(old_path):
        os.remove(old_path)
        print(f"删除旧文件: {old_path}")
    
    if os.path.exists(new_path):
        shutil.copy2(new_path, old_path)
        print(f"复制新文件: {new_path} -> {old_path}")
    
    print("✓ 完成!")
except Exception as e:
    print(f"✗ 错误: {e}")
