#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
【monitor_progress.py —— 逐轮训练监视器】
作用：训练在跑的时候，这个脚本另开一个终端运行，每 30 秒读一次 results.csv，
      把「每一轮」的 mAP / P / R / box_loss 追加写到 epoch_progress.txt，
      方便不盯屏幕也能随时看训练到第几轮、指标涨没涨。

注意：它【只监视、只记录】，不负责出报告（报告由 gen_docx.py 在训练结束后生成）。
"""

import os, time, csv

# ============ 路径 ============
ROOT = r"C:/Users/admin/WorkBuddy/2026-07-27-09-13-23/table-training"
CSV_PATH = os.path.join(ROOT, "runs", "cvat_tables", "results.csv")   # 训练实时写这个
PROG = os.path.join(ROOT, "..", "annotation-platforms", "epoch_progress.txt")  # 进度日志
PROG = os.path.abspath(PROG)


def train_running():
    """粗略判断 python 训练进程是否还在跑（看任务列表里有没有 python.exe）。"""
    import subprocess
    try:
        out = subprocess.check_output(["tasklist"], stderr=subprocess.DEVNULL).decode("gbk", "ignore")
        return "python.exe" in out
    except Exception:
        return True   # 判断失败就假设还在跑，别误停


last_epoch = -1
last_mtime = 0
print(f"[monitor] 开始监视 {CSV_PATH}", flush=True)
# 在进度日志里先写一段分隔标题（区分这次续训）
with open(PROG, "a", encoding="utf-8") as pf:
    pf.write(f"\n===== 续训轮次 (best.pt Epoch32 基础上) {time.strftime('%Y-%m-%d %H:%M')} =====\n")

# ============ 主循环：每 30 秒检查一次 ============
while True:
    try:
        if os.path.exists(CSV_PATH):
            mtime = os.path.getmtime(CSV_PATH)
            if mtime != last_mtime:   # 文件变了 = 有新的一轮写完
                last_mtime = mtime
                with open(CSV_PATH, newline="", encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                if rows:
                    r = rows[-1]                       # 取最后一行 = 最新一轮
                    ep = int(float(r["epoch"]))
                    if ep != last_epoch:               # 确实是新轮次才记录
                        last_epoch = ep
                        line = (f"Epoch {ep:>2} | mAP50={float(r['metrics/mAP50(B)']):.4f} "
                                f"| mAP50-95={float(r['metrics/mAP50-95(B)']):.4f} "
                                f"| P={float(r['metrics/precision(B)']):.4f} "
                                f"| R={float(r['metrics/recall(B)']):.4f} "
                                f"| box={float(r['train/box_loss']):.4f}")
                        print("[monitor]", line, flush=True)
                        with open(PROG, "a", encoding="utf-8") as pf:
                            pf.write(line + "\n")
    except Exception as e:
        print("[monitor] 读CSV出错:", e, flush=True)

    # 训练进程已退出，且 CSV 两分钟没变 → 认为训练结束，停止监视
    if not train_running() and (time.time() - os.path.getmtime(CSV_PATH) if os.path.exists(CSV_PATH) else 0) > 120:
        print("[monitor] 训练进程已退出，监视结束。", flush=True)
        break
    time.sleep(30)
