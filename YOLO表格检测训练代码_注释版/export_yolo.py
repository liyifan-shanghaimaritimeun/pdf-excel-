#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
【export_yolo.py —— 从 CVAT 导出 YOLO 数据集】
作用：把 CVAT 标注平台 Project 2 里的所有标注，转成 YOLOv8 训练需要的格式：
        images/train, images/val, labels/train, labels/val, 外加 data.yaml。

关键规则（已在中文注释里标出）：
  - CVAT 矩形坐标是 [x, y, w, h]（左上角+宽高），要转成 YOLO 的「归一化中心框」[xc,yc,bw,bh]
  - 「存活即采纳」：manual / semi-auto / 用户没删的 auto，全部纳入训练
  - 空壳 task（0 标注）跳过，不进训练集也不删除
  - 图片重命名为纯 ASCII（taskidx_frameno.png），避免 Windows 下 cv2 读非 ASCII 路径失败
  - 按「图片」做 train/val 划分（同一页的多框天然落在同一集合），seed 固定
"""

import os
import json
import shutil
import random
import importlib.util
import urllib.request
from PIL import Image

# ---- 复用治理脚本 cvat_dedup_regen.py 里的常量与函数 ----
# （TOKEN 鉴权、BASE 接口地址、PROJECT_ID 项目号；find_source/png_for_frame 找图函数）
SPEC = importlib.util.spec_from_file_location(
    "dr", r"C:/Users/admin/WorkBuddy/2026-07-27-09-13-23/annotation-platforms/cvat_dedup_regen.py"
)
dr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dr)

TOKEN = dr.TOKEN
BASE = dr.BASE
PROJECT_ID = dr.PROJECT_ID

# 导出目录：yolo_dataset（images/ + labels/ + data.yaml 都在这）
OUT = r"C:/Users/admin/WorkBuddy/2026-07-27-09-13-23/table-training/yolo_dataset"
TRAIN_RATIO = 0.8   # 80% 当训练集，20% 当验证集
SEED = 42           # 随机种子，保证每次划分结果一致
SIZE_CACHE = {}     # 图片尺寸缓存，避免重复打开图片算宽高


def api_get(path):
    """通用 GET 请求：带 Token 鉴权，返回解析后的 JSON。"""
    req = urllib.request.Request(BASE + path, headers={"Authorization": f"Token {TOKEN}"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def img_size(path):
    """读图片宽高并缓存，省得后面每框都重新打开。"""
    if path in SIZE_CACHE:
        return SIZE_CACHE[path]
    with Image.open(path) as im:
        sz = im.size
    SIZE_CACHE[path] = sz
    return sz


def main():
    random.seed(SEED)
    # 关键：导出前先清空旧的 images/labels 子目录，保证【全量覆盖】。
    # 否则上次导出的残留标签/图片会留下「你已删除的框」，造成数据污染。
    for sp in ("train", "val"):
        for sub in ("images", "labels"):
            d = os.path.join(OUT, sub, sp)
            if os.path.isdir(d):
                shutil.rmtree(d)
    # 再把 train/val 两套 images、labels 目录建好
    for sp in ("train", "val"):
        os.makedirs(os.path.join(OUT, "images", sp), exist_ok=True)
        os.makedirs(os.path.join(OUT, "labels", sp), exist_ok=True)

    # 拉取项目里定义的类别（标签），并固定「名称→下标」顺序
    lbls = api_get(f"/labels?project_id={PROJECT_ID}").get("results", [])
    lbls.sort(key=lambda x: x["id"])
    names = [l["name"] for l in lbls]
    id2name = {l["id"]: l["name"] for l in lbls}
    name2idx = {n: i for i, n in enumerate(names)}
    print("类别顺序:", names)

    # 拉取项目下所有 task（每个 task 对应一本 PDF 或一段材料）
    tasks = api_get(f"/tasks?project_id={PROJECT_ID}&page_size=1000").get("results", [])
    print(f"项目 {PROJECT_ID} 共 {len(tasks)} 个 task")

    # samples：收集所有「(图片, task序号, 页码, 类别, xc, yc, bw, bh)」
    samples = []
    per_class = [0] * len(names)          # 各类框数统计
    skipped_shape = skipped_img = no_folder = empty_tasks = 0
    src_counts = {}                        # 各来源框数（manual / semi-auto / auto）

    for ti, t in enumerate(tasks):
        name = t["name"]
        folder, _ = dr.find_source(name)   # 根据 task 名找到本地渲染好的图片目录
        if not folder:
            no_folder += 1
            print(f"  [跳过] 找不到图片目录: {name}")
            continue
        jobs = api_get(f"/jobs?task_id={t['id']}").get("results", [])
        task_boxes = 0
        for j in jobs:
            anno = api_get(f"/jobs/{j['id']}/annotations")
            for s in anno.get("shapes", []):
                if s.get("type") != "rectangle":
                    skipped_shape += 1
                    continue
                # ——「存活即采纳」——
                # CVAT 里"被你改过的 auto"仍标记 source='auto'，没有独立标记；
                # 所以只要这框还活着（没被你删），就当成有效标注导出。
                src = s.get("source", "unknown")
                src_counts[src] = src_counts.get(src, 0) + 1
                lid = s.get("label_id")
                if lid not in id2name:
                    skipped_shape += 1
                    continue
                cls = name2idx[id2name[lid]]
                f = s.get("frame", 0)
                img = dr.png_for_frame(folder, f)   # 第 f 页对应的 png 路径
                if not img:
                    skipped_img += 1
                    continue
                # CVAT 矩形：points=[x, y, w, h]
                x, y, w, h = [float(v) for v in s["points"]]
                if w <= 0 or h <= 0:
                    skipped_shape += 1
                    continue
                try:
                    W, H = img_size(img)
                except Exception:
                    skipped_img += 1
                    continue
                # 转 YOLO 归一化中心框：坐标除以宽高，并夹在 [0,1]
                xc = min(max((x + w / 2) / W, 0), 1)
                yc = min(max((y + h / 2) / H, 0), 1)
                bw = min(max(w / W, 0), 1)
                bh = min(max(h / H, 0), 1)
                per_class[cls] += 1
                task_boxes += 1
                samples.append((img, ti, f, cls, xc, yc, bw, bh))
        if task_boxes == 0:
            empty_tasks += 1
            print(f"  [跳过-空壳] 0 标注 task: {name}")

    # 按 (图片, task序号, 页码) 聚合同一页上的多个框 → 一个 txt 放一页所有框
    img_groups = {}
    for img, ti, f, cls, xc, yc, bw, bh in samples:
        img_groups.setdefault((img, ti, f), []).append((cls, xc, yc, bw, bh))

    # —— train/val 划分：按「图片」打乱后取前 80% 为训练 ——
    keys = list(img_groups.keys())
    random.shuffle(keys)
    n_train = int(len(keys) * TRAIN_RATIO)

    n_images = n_boxes = 0
    for i, key in enumerate(keys):
        img, ti, f = key
        boxes = img_groups[key]
        split = "train" if i < n_train else "val"
        base = f"{ti:03d}_{f:03d}"   # 纯 ASCII 文件名，避免中文路径坑
        dst_img = os.path.join(OUT, "images", split, base + ".png")
        dst_lbl = os.path.join(OUT, "labels", split, base + ".txt")
        if not os.path.exists(dst_img):
            shutil.copy(img, dst_img)
        # 写 label：每行 = "类别下标 xc yc bw bh"
        with open(dst_lbl, "w", encoding="utf-8") as fp:
            for cls, xc, yc, bw, bh in boxes:
                fp.write(f"{cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n")
        n_images += 1
        n_boxes += len(boxes)

    # 写 data.yaml：YOLO 训练时必须的「数据集说明书」
    yaml_path = os.path.join(OUT, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as fp:
        fp.write(f"path: {OUT}\n")
        fp.write("train: images/train\n")
        fp.write("val: images/val\n")
        fp.write(f"nc: {len(names)}\n")
        # names 用 JSON 写，保证中文不乱码
        fp.write("names: " + json.dumps(names, ensure_ascii=False) + "\n")

    # 打印导出汇总，方便核对
    print("\n===== 导出完成 =====")
    print(f"有效图片(task 内带标注的页): {n_images}  (train={n_train}, val={len(keys)-n_train})")
    print(f"标注框总数: {n_boxes}")
    print("各类框数:")
    for i, n in enumerate(per_class):
        print(f"  {names[i]}: {n}")
    print(f"跳过: 空壳 task={empty_tasks}, 无图片目录={no_folder}, 非矩形/未知标签={skipped_shape}, 缺图={skipped_img}")
    print("各来源框数(均纳入训练):", src_counts)
    print(f"数据集目录: {OUT}")
    print(f"data.yaml: {yaml_path}")


if __name__ == "__main__":
    main()
