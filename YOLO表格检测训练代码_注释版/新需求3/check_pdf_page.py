import fitz

pdf_path = "拉拉乐五金2026.pdf"
doc = fitz.open(pdf_path)

print(f"PDF文件: {pdf_path}")
print(f"总页数: {doc.page_count}")
print()

for page_num in range(min(5, doc.page_count)):
    page = doc[page_num]
    rect = page.rect
    print(f"第 {page_num + 1} 页:")
    print(f"  尺寸: {rect.width:.1f} x {rect.height:.1f}")
    print(f"  旋转角度: {page.rotation}")
    print(f"  横向/纵向: {'横向' if rect.width > rect.height else '纵向'}")
    print()
    
    text_blocks = page.get_text("blocks")
    print(f"  文字块数量: {len(text_blocks)}")
    
    for i, block in enumerate(text_blocks[:5]):
        x0, y0, x1, y1, text, _, _ = block
        width = x1 - x0
        height = y1 - y0
        print(f"    [{i}] text='{text[:30]}...' pos=({x0:.1f},{y0:.1f}) size=({width:.1f}x{height:.1f})")
    print()

doc.close()
