#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
【train_yolo.py —— 训练主程序】
作用：在导出的 YOLO 数据集上训练 YOLOv8n 检测模型（4 类：表格/表头/重点内容/型号）。
      纯 CPU 训练；训练完成后自动做验证、打印指标、把 best.pt 复制成固定名字的权重文件。

阅读顺序：
  1) 顶部常量：数据/输出路径
  2) main()：加载权重 → 训练 → 验证 → 导出 → 写指标 json
  3) __main__：异常捕获，训练崩了会把堆栈写进 train_error.log
"""

import os
import json
import sys

# ============ 1) 路径常量 ============
# ROOT：整个训练工程根目录（数据集、runs、报告都放在这里）
ROOT = r"C:/Users/admin/WorkBuddy/2026-07-27-09-13-23/table-training"
# DATA：YOLO 训练描述文件 data.yaml 的路径（里面写清类别名和 train/val 位置）
DATA = os.path.join(ROOT, "yolo_dataset", "data.yaml")
# RUNS：ultralytics 保存训练产物的目录（runs/cvat_tables/weights/best.pt）
RUNS = os.path.join(ROOT, "runs")
# MODEL_OUT：训练结束后，把 best.pt 复制成这个固定名字，方便后续直接调用
MODEL_OUT = os.path.join(ROOT, "cvat_yolov8n.pt")

# 引入 ultralytics 的 YOLO 接口（训练/验证/预测都靠它）
from ultralytics import YOLO


def main():
    # ============ 2) 加载预训练权重 ============
    # 当前是【续训】写法：在上一轮的最佳权重 best.pt（对应 Epoch32）基础上继续微调。
    # 如果想【从零训练 / 用官方预训练】，把下面这行换成：
    #   model = YOLO("yolov8n.pt")   # 官方 COCO 预训练权重
    model = YOLO(r"C:/Users/admin/WorkBuddy/2026-07-27-09-13-23/table-training/runs/cvat_tables/weights/best.pt")

    # ============ 3) 启动训练 ============
    results = model.train(
        data=DATA,            # 数据集描述文件
        task="detect",        # 任务类型：目标检测
        epochs=50,            # 最多训练 50 轮
        imgsz=640,            # 输入图像统一缩放到 640×640
        batch=4,              # 每批 4 张图（CPU 内存受限，不能太大）
        device="cpu",         # 用 CPU 训练（本机无 GPU）
        workers=0,            # 数据加载子进程数（Windows 下 0 最稳）
        optimizer="auto",     # 优化器自动选择
        lr0=0.001,            # 初始学习率
        patience=15,          # 验证指标连续 15 轮不再提升就【早停】，避免白跑
        seed=42,              # 随机种子固定，结果可复现
        name="cvat_tables",   # 本次 run 的名字（产物在 runs/cvat_tables/）
        project=RUNS,         # run 的父目录
        exist_ok=True,        # 同名 run 已存在则覆盖，不报错
        verbose=True,         # 打印详细日志
    )

    # ============ 4) 训练后验证 ============
    # 用验证集再跑一遍，得到 mAP / Precision / Recall 等最终指标
    metrics = model.val(data=DATA, imgsz=640, batch=8, device="cpu", verbose=False)
    print("\n===== 验证指标 =====")
    print("mAP50-95:", round(metrics.box.map, 4))    # 严格 IoU 阈值下的平均精度
    print("mAP50   :", round(metrics.box.map50, 4))  # IoU=0.5 下的平均精度（最常用）
    # 逐类 mAP（看看哪类学得好、哪类学得差）
    per_class = getattr(metrics.box, "maps", None)
    if per_class is not None:
        names = results.train_args.get("names") if hasattr(results, "train_args") else None
        print("各类 mAP50-95:", [round(float(x), 4) for x in per_class])

    # ============ 5) 导出最佳权重 ============
    # ultralytics 训练时会自动保存 best.pt；这里再复制一份成固定名字 MODEL_OUT
    best = os.path.join(RUNS, "cvat_tables", "weights", "best.pt")
    if os.path.exists(best):
        import shutil
        shutil.copy(best, MODEL_OUT)
        print("\n最佳权重已复制到:", MODEL_OUT)
    else:
        print("未找到 best.pt:", best)

    # ============ 6) 保存指标摘要 json ============
    # 把关键指标写进 train_metrics.json，供 gen_docx.py 生成报告时读取
    summary = {
        "map50_95": float(metrics.box.map),
        "map50": float(metrics.box.map50),
        "per_class_map50_95": [float(x) for x in per_class] if per_class is not None else None,
        "best_pt": MODEL_OUT if os.path.exists(MODEL_OUT) else best,
    }
    with open(os.path.join(ROOT, "train_metrics.json"), "w", encoding="utf-8") as fp:
        json.dump(summary, fp, ensure_ascii=False, indent=2)
    print("指标摘要已写入:", os.path.join(ROOT, "train_metrics.json"))


if __name__ == "__main__":
    # ============ 7) 异常兜底 ============
    # 训练如果中途崩溃，把完整堆栈写进 train_error.log，方便事后排查，而不是无声失败
    try:
        main()
    except Exception as e:
        import traceback
        with open(os.path.join(ROOT, "train_error.log"), "w", encoding="utf-8") as ef:
            ef.write("TRAIN CRASHED:\n")
            traceback.print_exc(file=ef)
        print("TRAIN CRASHED:", repr(e), flush=True)
        traceback.print_exc()
        raise
