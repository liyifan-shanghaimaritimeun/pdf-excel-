#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【vis_compare.py —— 生成对照例图】
作用：把「你的手动标注(GT)」和「模型预测」画在同一张图上，直观看模型学得对不对。
      - 蓝框 + 半透明蓝填充 + 加粗描边 + 最顶层  = 你的标注(GT, Ground Truth)
      - 绿框 = 预测正确（和某个蓝框 IoU≥0.5 且同类）
      - 红框 = 预测错误（误检 / 错位）
      - 整页级（>45%图面积）且低置信度(<0.5) 的预测框会被隐藏，避免盖住整张图当噪声

逻辑分层（关键在最后 3 段 draw）：
  第1层 预测框（最底）
  第2层 GT 半透明填充（中间）
  第3层 GT 描边+标签（最顶，永远最醒目）
"""

import os, random
from PIL import Image, ImageDraw
from ultralytics import YOLO

# ============ 路径与参数 ============
BASE = r"C:\Users\admin\WorkBuddy\2026-07-27-09-13-23"
IMG_DIR = os.path.join(BASE, "table-training", "yolo_dataset", "images", "val")  # 用验证集图
LAB_DIR = os.path.join(BASE, "table-training", "yolo_dataset", "labels", "val")  # 对应的 GT 标签
WEIGHTS = os.path.join(BASE, "table-training", "runs", "cvat_tables", "weights", "best.pt")
OUT = os.path.join(BASE, "table-training", "example_vis")   # 对照图输出目录
os.makedirs(OUT, exist_ok=True)

# 类别名（和 data.yaml 顺序一致）
NAMES = ["表格", "表头", "重点内容", "型号"]
GT_COLOR = (0, 110, 255)        # 鲜亮蓝（你的标注）
GT_FILL = (0, 110, 255, 55)     # 半透明蓝填充
GT_LABEL_BG = (220, 235, 255)   # GT 标签浅蓝底
TP_COLOR = (0, 170, 0)           # 绿=预测正确
FP_COLOR = (220, 0, 0)           # 红=预测错误
PRED_LABEL_BG = (255, 255, 255) # 预测标签白底
CONF_THRESH = 0.4                # 预测置信度门槛（平衡精度与召回；部署用 model.predict(conf=0.4)）
PAGE_RATIO = 0.45                # 面积占比超过这个算"整页级"
CONF_PAGE = 0.5                  # 整页级框要过滤掉的置信度门槛

model = YOLO(WEIGHTS)   # 加载训练好的权重


def load_gt(lab_path, W, H):
    """读 GT 标签文件，把 YOLO 归一化框还原成像素坐标 [x1,y1,x2,y2,类别]。"""
    gts = []
    if os.path.exists(lab_path):
        for line in open(lab_path):
            p = line.split()
            if len(p) < 5:
                continue
            cid = int(p[0]); xc = float(p[1]); yc = float(p[2]); bw = float(p[3]); bh = float(p[4])
            x = (xc - bw / 2) * W; y = (yc - bh / 2) * H
            gts.append([int(x), int(y), int(x + bw * W), int(y + bh * H), cid])
    return gts


def iou(a, b):
    """算两个框的交并比 IoU（判断预测是否命中 GT）。"""
    xa = max(a[0], b[0]); ya = max(a[1], b[1])
    xb = min(a[2], b[2]); yb = min(a[3], b[3])
    iw = max(0, xb - xa); ih = max(0, yb - ya)
    inter = iw * ih
    if inter == 0:
        return 0
    aa = (a[2] - a[0]) * (a[3] - a[1]); ab = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (aa + ab - inter)


def text_w(draw, s):
    """粗略估算文字像素宽度（PIL 默认字体约 7px/字）。"""
    return len(s) * 7


# ============ 选图：挑 GT 框≥3 且不是"整页单一大框"的图，对照才好看 ============
imgs = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
random.seed(7)
selected = []
for f in imgs:
    im = Image.open(os.path.join(IMG_DIR, f)); W, H = im.size
    gts = load_gt(os.path.join(LAB_DIR, os.path.splitext(f)[0] + ".txt"), W, H)
    if len(gts) >= 3:
        # 排除"只有1~2个框且最大框占了85%图面积"的整页级图（蓝框会盖住一切）
        if not (len(gts) <= 2 and max((g[2]-g[0]) * (g[3]-g[1]) for g in gts) / (W*H) > 0.85):
            selected.append(f)
random.shuffle(selected)

# ============ 逐张出图 ============
count = 0
for f in selected[:6]:   # 最多画 6 张
    im = Image.open(os.path.join(IMG_DIR, f)).convert("RGBA"); W, H = im.size
    gts = load_gt(os.path.join(LAB_DIR, os.path.splitext(f)[0] + ".txt"), W, H)
    # 模型预测这一张图
    res = model.predict(os.path.join(IMG_DIR, f), conf=CONF_THRESH, iou=0.5, verbose=False)[0]
    preds = []
    if res.boxes is not None:
        for b, c, cf in zip(res.boxes.xyxy, res.boxes.cls, res.boxes.conf):
            preds.append([int(b[0]), int(b[1]), int(b[2]), int(b[3]), int(c), float(cf)])

    # —— 第 1 层：画预测框（最底）——
    draw = ImageDraw.Draw(im)
    used = [False] * len(gts)   # 记录哪些 GT 已被预测命中
    for p in preds:
        area = (p[2] - p[0]) * (p[3] - p[1])
        # 整页级 + 低置信度 → 隐藏（视觉噪声）
        if area / (W*H) > PAGE_RATIO and p[5] < CONF_PAGE:
            continue
        best = -1; best_iou = 0
        for i, g in enumerate(gts):
            if used[i] or g[4] != p[4]:   # 类别不同不算命中
                continue
            v = iou(p, g)
            if v > best_iou:
                best_iou = v; best = i
        if best >= 0 and best_iou >= 0.5:
            used[best] = True
            col = TP_COLOR   # 命中 → 绿
        else:
            col = FP_COLOR   # 未命中 → 红
        tag = f"{NAMES[p[4]]} {p[5]:.2f}"
        draw.rectangle([p[0], p[1], p[2], p[3]], outline=col, width=2)
        tw = text_w(draw, tag)
        draw.rectangle([p[0], max(0, p[1] - 14), p[0] + tw + 4, p[1]], fill=PRED_LABEL_BG)
        draw.text((p[0] + 2, max(0, p[1] - 13)), tag, fill=col)

    # —— 第 2 层：GT 半透明填充（中间，不抢戏但醒目）——
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    for g in gts:
        o_draw.rectangle([g[0], g[1], g[2], g[3]], fill=GT_FILL)
    im = Image.alpha_composite(im, overlay).convert("RGB")

    # —— 第 3 层：GT 描边 + 标签（最顶，永远最醒目）——
    draw = ImageDraw.Draw(im)
    for g in gts:
        draw.rectangle([g[0], g[1], g[2], g[3]], outline=GT_COLOR, width=3)  # 加粗3px
        tag = f"GT:{NAMES[g[4]]}"
        tw = text_w(draw, tag)
        ly = min(H - 16, g[3] + 1)   # 标签放框底部
        draw.rectangle([g[0], ly, g[0] + tw + 4, ly + 15], fill=GT_LABEL_BG)
        draw.text((g[0] + 2, ly + 1), tag, fill=GT_COLOR)

    im.save(os.path.join(OUT, f))
    count += 1
    print("saved", os.path.join(OUT, f), "GT=", len(gts), "preds_shown=", sum(
        1 for p in preds if not ((p[2]-p[0])*(p[3]-p[1])/(W*H) > PAGE_RATIO and p[5] < CONF_PAGE)
    ))
print("done total =", count)
