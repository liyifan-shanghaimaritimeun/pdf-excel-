from paddleocr import PaddleOCR

ocr = PaddleOCR(lang='ch', use_gpu=False, show_log=False)
result = ocr.ocr('_test.png', cls=True)

items = result[0]
for i, item in enumerate(items):
    box = item[0]
    text = item[1][0]
    x0, y0 = box[0]
    x1, y1 = box[2]
    print(f"{i:3d}: y={y0:6.1f}-{y1:6.1f}, x={x0:6.1f}-{x1:6.1f}, text={text[:60]}")