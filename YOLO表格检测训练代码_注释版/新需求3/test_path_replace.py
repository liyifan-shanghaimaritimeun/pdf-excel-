import os

path = r"C:\Users\admin\Desktop\新需求3\测试\models\whl\det\ch\ch_PP-OCRv4_det_infer"

print(f"原始路径: {path}")
print(f"原始路径repr: {repr(path)}")

path_fixed = path.replace('\\', '/')
print(f"替换后路径: {path_fixed}")
print(f"替换后路径repr: {repr(path_fixed)}")

file_path = os.path.join(path_fixed, 'inference.pdmodel')
print(f"拼接后路径: {file_path}")

file_path2 = path_fixed + '/inference.pdmodel'
print(f"直接拼接: {file_path2}")

exists = os.path.exists(path_fixed)
print(f"路径存在: {exists}")

if exists:
    files = os.listdir(path_fixed)
    print(f"目录内容: {files}")
