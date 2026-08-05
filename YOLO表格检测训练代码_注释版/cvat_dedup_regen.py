#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
【cvat_dedup_regen.py —— 复用的 CVAT 治理工具（共享辅助脚本）】
★ 这是被 export_yolo.py 和 clear_auto.py 直接 import 复用的底层脚本，放在这里是为了让
  桌面这份副本能独立跑通（它们靠本文件拿 TOKEN / BASE / PROJECT_ID 和 API 辅助函数）。

它负责三件事（命令行参数切换）：
  --dedup   删除同名重复 task（保留 id 最小那份），清理空壳副本
  --regen   对每个唯一 task 从 PDF 重新生成【所有页】auto 标注；只删 source=='auto' 旧框，
            保留 manual / semi-auto 手动标注；find_tables 有 text 回退，补漏无网格线的表
  --dry-run 只打印将做什么，不实际改动（安全预检）

★ 关键 API 坑（已在此脚本里处理好，记一下免得再踩）：
  - 删除框要用 PATCH /jobs/<id>/annotations?action=delete，且每个待删 shape 必须带
    完整字段（type/label_id/frame 等），不能只传 id
  - 大请求要分批（每批 1000）且 version 本地自增 1，否则 300s 超时或乐观锁报错丢标注

用法示例：
  python cvat_dedup_regen.py --dedup --dry-run
  python cvat_dedup_regen.py --dedup
  python cvat_dedup_regen.py --regen --dry-run
  python cvat_dedup_regen.py --regen
  python cvat_dedup_regen.py --regen --task "<某个task名>"   # 单个 task 验证
"""

import os
import re
import sys
import json
import time
import fitz
import urllib.request
import urllib.error
from collections import defaultdict

# ============ CVAT 连接与项目常量 ============
TOKEN = "39b8bd237b55e6cf03a07cb0d78b65372ba08d1b"   # 登录 Token（admin/admin）
BASE = "http://localhost:8080/api"                    # CVAT REST API 根地址
PROJECT_ID = 2                                         # 标注项目号（表格检测 Project 2）

# 类别名 → label_id 映射（和 CVAT 里一致）
LABEL = {"表格": 1, "表头": 2, "重点内容": 3, "型号": 4}

# 电气型号正则（用于在文本里抓型号）
MODEL_RE = re.compile(r'\b[A-Z]{2,4}[-\s]?\d{1,3}[A-Z]?\b')
# 认证/标准号关键词，避免把 ISO9001 / RoHS / CCC 等误标为型号
CERT_KW = re.compile(r'ISO|IEC|GB/T|CCC|RoHS|CE|UL|认证|certif', re.I)

# 渲染好的图片根目录（PDF 每页转成的 png 放这里）
IMG_ROOT = r"C:\Users\admin\WorkBuddy\2026-07-27-09-13-23\table-training\data\images"
# 可能的 PDF 源目录（按 task 名去找 <目录>/<task名>.pdf）
PDF_DIRS = [
    r"C:\Users\admin\Desktop\正泰电气",
    r"C:\Users\admin\Desktop\新需求3\最新目录PDF",
    r"C:\Users\admin\Desktop\测试数据\测试数据\元器件—识别产品型号",
    r"C:\Users\admin\Desktop\测试数据\测试数据\零部件—识别产品系列",
]


# ---------- CVAT API 通用封装 ----------
def api(method, path, body=None):
    """发一个 CVAT 请求，返回 (HTTP状态码, 解析后的JSON或原始文本)。"""
    headers = {"Authorization": f"Token {TOKEN}"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read().decode()
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:800]


def _patch_annotations(job_id, action, shapes, version, batch=1000):
    """分批 PATCH 注解（create/delete），避免大请求超时。
       CVAT 每次 PATCH 成功后 version 仅 +1，所以这里本地自增 v。返回 (ok, last_version)。"""
    ok = True
    v = version
    if not shapes:
        return ok, v
    for i in range(0, len(shapes), batch):
        chunk = shapes[i:i + batch]
        if action == "delete":
            # delete 必须带完整 shape 对象（含 id/type/label_id/frame 等）
            payload = {"version": v, "shapes": chunk, "tracks": [], "tags": []}
        else:  # create
            cvat = []
            for name, box, frame in chunk:
                x, y, w, h = [float(vv) for vv in box]
                cvat.append({
                    "type": "rectangle", "label_id": LABEL[name], "frame": int(frame),
                    "points": [x, y, w, h], "occluded": False, "z_order": 0,
                    "group": 0, "attributes": [], "source": "auto",
                })
            payload = {"version": v, "tags": [], "shapes": cvat, "tracks": []}
        st, _ = api("PATCH", f"/jobs/{job_id}/annotations?action={action}", payload)
        if st not in (200, 201):
            ok = False
            break
        v += 1  # 每次成功 PATCH，version 自增 1
    return ok, v


def get_jobs(task_id):
    """取某个 task 下所有 job。"""
    st, d = api("GET", f"/jobs?task_id={task_id}")
    return d.get("results", []) if st == 200 else []


def get_job_annotations(job_id):
    """读某个 job 的注解，返回 (version, shapes)。"""
    st, d = api("GET", f"/jobs/{job_id}/annotations")
    if st == 200:
        return d.get("version", 1), d.get("shapes", [])
    return None, []


def remove_shapes(job_id, auto_shapes, version):
    """删除指定框（对外封装，clear_auto.py 用它）。"""
    ok, _ = _patch_annotations(job_id, "delete", auto_shapes, version)
    return 200 if ok else 400


def create_shapes(job_id, fresh, version):
    """新建框（对外封装，regen 用它）。"""
    ok, _ = _patch_annotations(job_id, "create", fresh, version)
    return (200 if ok else 400), len(fresh)


# ---------- 源定位（task 名 → 本地图片目录 / PDF） ----------
def find_source(task_name):
    """根据 task 名找本地图片目录和 PDF 源文件，返回 (folder, pdf)。"""
    folder = None
    for cand in [os.path.join(IMG_ROOT, "正泰", task_name), os.path.join(IMG_ROOT, task_name)]:
        if os.path.isdir(cand):
            folder = cand
            break
    pdf = None
    for d in PDF_DIRS:
        cand = os.path.join(d, task_name + ".pdf")
        if os.path.exists(cand):
            pdf = cand
            break
    return folder, pdf


def png_for_frame(folder, frame):
    """第 frame 页对应的 png（page_001.png 从 frame=0 起）。"""
    p = os.path.join(folder, f"page_{frame+1:03d}.png")
    return p if os.path.exists(p) else None


# ---------- 增强版 PDF → shapes（自动标注核心） ----------
def gen_page_shapes(page, png_w, png_h):
    """对一页 PDF 生成 auto 标注框列表 [(类别名, [x,y,w,h], None), ...]。"""
    zoom_x = png_w / page.rect.width
    zoom_y = png_h / page.rect.height

    def to_box(rect):
        x0, y0, x1, y1 = rect
        return [x0 * zoom_x, y0 * zoom_y, (x1 - x0) * zoom_x, (y1 - y0) * zoom_y]

    shapes = []
    # 表格检测：lines 策略优先，找不到回退 text 策略（补漏无网格线但按文字对齐的表）
    tables = []
    for kw in (dict(horizontal_strategy="lines", vertical_strategy="lines"),
               dict(horizontal_strategy="text", vertical_strategy="text")):
        try:
            found = page.find_tables(**kw)
            if found.tables:
                tables = found.tables
                break
        except Exception:
            continue
    for t in tables:
        shapes.append(("表格", to_box(t.bbox), None))       # 整表外框
        rows = t.rows
        if rows:
            shapes.append(("表头", to_box(rows[0].bbox), None))   # 首行=表头
            for r in rows[1:]:
                shapes.append(("重点内容", to_box(r.bbox), None)) # 其余行=重点内容

    # 型号：逐文本 span 用正则抓
    try:
        d = page.get_text("dict")
        for block in d.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    txt = span.get("text", "")
                    if MODEL_RE.search(txt) and not CERT_KW.search(txt):
                        shapes.append(("型号", to_box(span["bbox"]), None))
    except Exception as e:
        print(f"    [warn] 型号提取失败: {e}")

    # 补漏：整页无表格/无型号、但有明显矢量图（尺寸图/示意图）的页，整图标为重点内容，
    # 仅当图元占页面 >=3% 面积，规避边框/水印误标
    if not shapes:
        try:
            draws = page.get_drawings()
            if draws:
                xs0 = [dr["rect"].x0 for dr in draws]
                ys0 = [dr["rect"].y0 for dr in draws]
                xs1 = [dr["rect"].x1 for dr in draws]
                ys1 = [dr["rect"].y1 for dr in draws]
                x0, y0, x1, y1 = min(xs0), min(ys0), max(xs1), max(ys1)
                area = (x1 - x0) * (y1 - y0)
                if area > 0.03 * page.rect.width * page.rect.height:
                    shapes.append(("重点内容", to_box((x0, y0, x1, y1)), None))
        except Exception:
            pass
    return shapes


# ---------- regen 单个 job（重新生成 auto 框） ----------
def regen_job(job, pdf, folder, dry_run=True):
    """对单个 job：删旧 auto 框 → 从 PDF 重新生成新 auto 框；保留 manual/semi-auto。"""
    jid = job["id"]
    sf = job.get("start_frame", 0)
    ef = job.get("stop_frame", 0)
    version, shapes = get_job_annotations(jid)
    if version is None:
        print(f"    [跳过] job {jid} 无法读取注解")
        return 0, 0, 0
    auto_shapes = [s for s in shapes if s.get("source") == "auto"]
    manual_n = len(shapes) - len(auto_shapes)
    doc = fitz.open(pdf)
    fresh = []
    for f in range(sf, ef + 1):
        png = png_for_frame(folder, f)
        if not png:
            continue
        pix = fitz.Pixmap(png)
        page = doc[f]
        for name_lbl, box, _ in gen_page_shapes(page, pix.width, pix.height):
            fresh.append((name_lbl, box, f))
    doc.close()

    if dry_run:
        print(f"    [dry] job {jid} 帧[{sf}-{ef}] 将删 auto={len(auto_shapes)} 保留手动={manual_n} 将建新框={len(fresh)}")
        return 0, len(auto_shapes), len(fresh)
    # 1) 删旧 auto 框
    if auto_shapes:
        st = remove_shapes(jid, auto_shapes, version)
        if st not in (200, 201):
            print(f"    [错误] job {jid} 删除 auto 框失败 HTTP {st}")
            return 0, 0, 0
        version, _ = get_job_annotations(jid)   # 删除后 version 自增，重新读
    # 2) 建新框
    if fresh:
        st, cnt = create_shapes(jid, fresh, version)
        if st not in (200, 201):
            print(f"    [错误] job {jid} 新建框失败 HTTP {st}")
            return 0, len(auto_shapes), 0
        return cnt, len(auto_shapes), len(fresh)
    return 0, len(auto_shapes), 0


def regen_task(task, dry_run=True):
    """对一个 task 下所有 job 做 regen。"""
    tid = task["id"]
    name = task["name"]
    folder, pdf = find_source(name)
    if not pdf or not folder:
        print(f"  [跳过] task {tid} {name!r}: 无 PDF 源（手动/拉拉乐类）→ 保留原样")
        return
    print(f"  [处理] task {tid} {name!r}")
    total_new = 0
    for job in get_jobs(tid):
        n, _, _ = regen_job(job, pdf, folder, dry_run)
        total_new += n
    if not dry_run:
        print(f"    -> 本 task 新建 {total_new} 框")


# ---------- 去重 ----------
def dedup(dry_run=True):
    """按名字分组，删除同名重复 task（保留最小 id）。"""
    st, d = api("GET", f"/tasks?project_id={PROJECT_ID}&page_size=1000")
    tasks = d.get("results", []) if st == 200 else []
    groups = defaultdict(list)
    for t in tasks:
        groups[t["name"]].append(t["id"])
    total_del = 0
    for name, ids in groups.items():
        if len(ids) <= 1:
            continue
        keep = min(ids)  # 保留最低 id（最早/最规范）
        for tid in ids:
            if tid == keep:
                continue
            total_del += 1
            if dry_run:
                print(f"  [dry] 将删除重复 task {tid} {name!r}（保留 {keep}）")
            else:
                st2, _ = api("DELETE", f"/tasks/{tid}")
                print(f"  删除 task {tid} {name!r} -> HTTP {st2}")
    print(f"\n去重{'预览' if dry_run else '完成'}: 重复组={sum(1 for v in groups.values() if len(v)>1)} 将删/已删={total_del}")


# ---------- 主流程（命令行入口） ----------
def main():
    args = sys.argv[1:]
    do_dedup = "--dedup" in args
    do_regen = "--regen" in args
    dry = "--dry-run" in args
    if not (do_dedup or do_regen):
        print("用法: --dedup | --regen | 组合，可加 --dry-run")
        return
    if do_dedup:
        print("===== 去重 =====")
        dedup(dry_run=dry)
    if do_regen:
        print("\n===== 重新全量标注（仅 auto，保留手动）=====")
        st, d = api("GET", f"/tasks?project_id={PROJECT_ID}&page_size=1000")
        tasks = d.get("results", []) if st == 200 else []
        print(f"项目 {PROJECT_ID} 共 {len(tasks)} 个 task")
        if "--task" in args:   # 单 task 验证模式
            tname = args[args.index("--task") + 1]
            t = next((t for t in tasks if t["name"] == tname), None)
            if not t:
                print("未找到 task:", tname)
                return
            regen_task(t, dry_run=dry)
            return
        total = 0
        for t in tasks:
            regen_task(t, dry_run=dry)
            time.sleep(0.1)
        print(f"\n{'[dry] ' if dry else ''}regen 完成")


if __name__ == "__main__":
    main()
