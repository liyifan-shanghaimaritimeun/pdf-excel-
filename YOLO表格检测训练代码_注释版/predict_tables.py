#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【predict_tables.py —— 开箱即用的表格检测推理脚本】

作用：拿本目录 weights/ 下的权重，对「图片 / 图片文件夹 / PDF」做表格检测，
      输出两样东西：
        1) 画好框的可视化图片  →  输出目录/vis/*.png
        2) 结构化坐标 JSON     →  输出目录/detections.json

和训练脚本的区别：这个脚本**不依赖工作区任何路径**，只依赖本目录的 weights/，
拷到任何一台装了 ultralytics 的机器上都能直接跑。

--------------------------------------------------------------------
用法示例（在本目录下打开命令行）：

  # 1) 跑单张图片
  python predict_tables.py -i 某页.png

  # 2) 跑整个图片文件夹
  python predict_tables.py -i ./测试数据/元器件—识别产品型号 -o ./out

  # 3) 直接跑 PDF（自动按 150 DPI 逐页渲染，需要 pip install pymupdf）
  python predict_tables.py -i 产品样册.pdf -o ./out

  # 4) 换成高召回权重（宁可多框、不愿漏框时用）
  python predict_tables.py -i 某页.png -w weights/table_high_recall.pt

  # 5) 只要「表格」这一类，并调低阈值多捞一些
  python predict_tables.py -i 某页.png --classes 0 --conf 0.15
--------------------------------------------------------------------
"""

import os
import sys
import json
import glob
import argparse

from PIL import Image, ImageDraw, ImageFont

# ============ 类别定义（训练时的顺序，不可改）============
# 0=表格  1=表头  2=重点内容  3=型号
CLASS_NAMES = {0: "表格", 1: "表头", 2: "重点内容", 3: "型号"}

# 每类画框用的颜色（RGB）
CLASS_COLORS = {
    0: (0, 120, 255),    # 表格 —— 蓝
    1: (255, 140, 0),    # 表头 —— 橙
    2: (0, 170, 90),     # 重点内容 —— 绿
    3: (220, 40, 60),    # 型号 —— 红
}

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_WEIGHTS = os.path.join(HERE, "weights", "table_best.pt")

IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")


# ---------------------------------------------------------------
# 1) 收集输入：把「单图 / 文件夹 / PDF」统一变成一串图片路径
# ---------------------------------------------------------------
def collect_inputs(src: str, workdir: str, dpi: int = 150):
    """返回 [(显示名, 图片绝对路径), ...]。PDF 会先渲染成 PNG 落到 workdir/pages/。"""
    src = os.path.abspath(src)

    # --- 情况 A：PDF，逐页渲染 ---
    if os.path.isfile(src) and src.lower().endswith(".pdf"):
        try:
            import fitz  # PyMuPDF
        except ImportError:
            sys.exit("[错误] 处理 PDF 需要 PyMuPDF，请先执行：pip install pymupdf")

        page_dir = os.path.join(workdir, "pages")
        os.makedirs(page_dir, exist_ok=True)
        doc = fitz.open(src)
        stem = os.path.splitext(os.path.basename(src))[0]
        out = []
        # DPI/72 是 PyMuPDF 的缩放倍率换算（PDF 内部单位是 72 dpi 的 point）
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        for i, page in enumerate(doc, start=1):
            p = os.path.join(page_dir, f"{stem}_page_{i:03d}.png")
            page.get_pixmap(matrix=mat).save(p)
            out.append((f"{stem}_page_{i:03d}", p))
        doc.close()
        print(f"[输入] PDF 共 {len(out)} 页，已按 {dpi} DPI 渲染到 {page_dir}")
        return out

    # --- 情况 B：单张图片 ---
    if os.path.isfile(src):
        return [(os.path.splitext(os.path.basename(src))[0], src)]

    # --- 情况 C：文件夹（递归找图）---
    if os.path.isdir(src):
        files = []
        for ext in IMG_EXT:
            files += glob.glob(os.path.join(src, "**", f"*{ext}"), recursive=True)
        files = sorted(set(files))
        print(f"[输入] 文件夹内找到 {len(files)} 张图片")
        return [(os.path.splitext(os.path.basename(f))[0], f) for f in files]

    sys.exit(f"[错误] 输入路径不存在：{src}")


# ---------------------------------------------------------------
# 2) 画框：把检测结果画到图上
# ---------------------------------------------------------------
def draw_boxes(img_path: str, boxes: list, out_path: str):
    """boxes 元素形如 {'cls':0,'name':'表格','conf':0.83,'xyxy':[x1,y1,x2,y2]}"""
    im = Image.open(img_path).convert("RGB")
    dr = ImageDraw.Draw(im)

    # 字号随图片大小自适应，避免大图上标签小得看不见
    font_size = max(14, int(im.width / 60))
    try:
        # 优先用系统中文字体，否则中文类名会显示成方框
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", font_size)
    except Exception:
        font = ImageFont.load_default()

    # 线宽也随图放大，小图 2px、大图更粗
    lw = max(2, int(im.width / 400))

    for b in boxes:
        x1, y1, x2, y2 = b["xyxy"]
        color = CLASS_COLORS.get(b["cls"], (128, 128, 128))
        dr.rectangle([x1, y1, x2, y2], outline=color, width=lw)

        label = f'{b["name"]} {b["conf"]:.2f}'
        # 量出标签文字占多大，好画一块同色底板（白字压在纯色上才看得清）
        tb = dr.textbbox((0, 0), label, font=font)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        # 框顶部放不下标签时（贴到图片上沿），就把标签挪到框内侧
        ty = y1 - th - 6 if y1 - th - 6 > 0 else y1 + 2
        dr.rectangle([x1, ty, x1 + tw + 8, ty + th + 6], fill=color)
        dr.text((x1 + 4, ty + 3), label, fill=(255, 255, 255), font=font)

    im.save(out_path)


# ---------------------------------------------------------------
# 3) 主流程
# ---------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="表格检测推理（4 类：表格/表头/重点内容/型号）")
    ap.add_argument("-i", "--input", required=True, help="图片 / 图片文件夹 / PDF 路径")
    ap.add_argument("-o", "--output", default=os.path.join(HERE, "predict_out"), help="输出目录")
    ap.add_argument("-w", "--weights", default=DEFAULT_WEIGHTS, help="权重路径")
    ap.add_argument("--conf", type=float, default=0.10,
                    help="置信度阈值，越低框越多（默认 0.10，定稿工作点：约 4 框/页，"
                         "IoU0.3 召回 0.742；追求更高召回可降到 0.05）")
    ap.add_argument("--iou", type=float, default=0.45, help="NMS 的 IoU 阈值（默认 0.45）")
    ap.add_argument("--classes", type=int, nargs="*", default=None,
                    help="只保留指定类别，如 --classes 0 3（默认全部 4 类）")
    ap.add_argument("--dpi", type=int, default=150, help="PDF 渲染 DPI（默认 150，与训练数据一致）")
    ap.add_argument("--no-vis", action="store_true", help="只出 JSON，不画图（批量跑得更快）")
    args = ap.parse_args()

    if not os.path.exists(args.weights):
        sys.exit(f"[错误] 权重不存在：{args.weights}")

    os.makedirs(args.output, exist_ok=True)
    vis_dir = os.path.join(args.output, "vis")
    if not args.no_vis:
        os.makedirs(vis_dir, exist_ok=True)

    items = collect_inputs(args.input, args.output, dpi=args.dpi)
    if not items:
        sys.exit("[错误] 没有找到任何可处理的图片")

    from ultralytics import YOLO
    print(f"[模型] 加载 {args.weights}")
    model = YOLO(args.weights)

    results = []
    total_boxes = 0

    for idx, (name, path) in enumerate(items, start=1):
        # device="cpu"：本机无独显，强制 CPU，避免 ultralytics 误判设备
        r = model.predict(path, conf=args.conf, iou=args.iou,
                          verbose=False, device="cpu")[0]

        boxes = []
        for b in r.boxes:
            cid = int(b.cls[0])
            if args.classes is not None and cid not in args.classes:
                continue
            x1, y1, x2, y2 = [round(v, 1) for v in b.xyxy[0].tolist()]
            boxes.append({
                "cls": cid,
                "name": CLASS_NAMES.get(cid, str(cid)),
                "conf": round(float(b.conf[0]), 4),
                "xyxy": [x1, y1, x2, y2],
            })

        # 同类内按置信度从高到低排，方便下游「取最可信的那个表」
        boxes.sort(key=lambda d: (d["cls"], -d["conf"]))
        total_boxes += len(boxes)

        W, H = Image.open(path).size
        results.append({"name": name, "image": path, "width": W, "height": H, "boxes": boxes})

        if not args.no_vis:
            draw_boxes(path, boxes, os.path.join(vis_dir, f"{name}.png"))

        # 每张都打一行，方便边跑边看有没有整页空框
        stat = {}
        for b in boxes:
            stat[b["name"]] = stat.get(b["name"], 0) + 1
        print(f"  [{idx}/{len(items)}] {name}: {len(boxes)} 框 {stat if stat else '(无检出)'}")

    json_path = os.path.join(args.output, "detections.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 共 {len(items)} 张图，检出 {total_boxes} 个框")
    print(f"  坐标 JSON : {json_path}")
    if not args.no_vis:
        print(f"  可视化图  : {vis_dir}")


if __name__ == "__main__":
    main()
