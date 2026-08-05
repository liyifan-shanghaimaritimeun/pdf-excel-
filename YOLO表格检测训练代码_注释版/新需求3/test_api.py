"""
检查 paddleocr 3.7.0 API
"""
import paddleocr

print(f"版本: {paddleocr.__version__}")

# 列出所有公开属性
attrs = [a for a in dir(paddleocr) if not a.startswith('_')]
print(f"\n公开属性: {attrs}")

# 检查关键类
for name in ['PPStructure', 'PPStructureV3', 'PP-Structure', 'PaddleOCR']:
    if hasattr(paddleocr, name):
        print(f"\n{name} 存在")
    else:
        print(f"\n{name} 不存在")

# 检查 paddleocr.structure
if hasattr(paddleocr, 'structure'):
    print(f"\npaddleocr.structure 存在")
    structure_attrs = [a for a in dir(paddleocr.structure) if not a.startswith('_')]
    print(f"  属性: {structure_attrs}")
