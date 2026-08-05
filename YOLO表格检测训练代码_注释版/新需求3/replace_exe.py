import os

old_path = r"C:\Users\admin\Desktop\新需求3\测试\PDF表格提取器.exe"
new_path = r"C:\Users\admin\Desktop\新需求3\测试\PDF表格提取器_new.exe"

try:
    if os.path.exists(old_path):
        os.remove(old_path)
        print(f"删除旧文件: {old_path}")
    
    if os.path.exists(new_path):
        os.rename(new_path, old_path)
        print(f"重命名新文件: {new_path} -> {old_path}")
    
    print("✓ 完成!")
except Exception as e:
    print(f"✗ 错误: {e}")
