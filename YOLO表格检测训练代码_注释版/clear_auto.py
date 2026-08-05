#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
【clear_auto.py —— 清空自动标注】
作用：把 CVAT Project 2 里的【自动标注(auto)】全部删除，只保留人工产生的标注
      （manual 纯手动 / semi-auto 半自动）。用于「先清掉机器乱标的，再用干净人工标注重训」。

三种运行模式（看命令行参数）：
  (无参数)    实际删除所有 auto 框，保留 manual/semi-auto
  --stats     只统计各来源分布，不改动任何标注
  --dry-run   统计 + 列出每个 task 将删多少 auto，但仍不改动（先预览）
  --also-semi 连 semi-auto 一起删，只留纯 manual（默认保留 semi-auto）

底层删除复用 cvat_dedup_regen 的 api / get_jobs / get_job_annotations / remove_shapes，
走分批 PATCH delete、version 本地自增，和「全页重生」的删除逻辑一致，避免乐观锁冲突。
"""

import sys
import importlib.util

# 复用治理脚本 cvat_dedup_regen.py（里面封装了 CVAT 的增删改查）
SPEC = importlib.util.spec_from_file_location(
    "dr", r"C:/Users/admin/WorkBuddy/2026-07-27-09-13-23/annotation-platforms/cvat_dedup_regen.py"
)
dr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dr)

# 注：PY 这一行原脚本里预留了 venv 解释器路径，这里保留以便需要时直接调用
PY = r"C:/Users/admin/.workbuddy/binaries/python/envs/default/Scripts/python.exe"


def main():
    # ============ 1) 解析运行模式 ============
    args = sys.argv[1:]
    stats_mode = "--stats" in args     # 仅统计
    dry = "--dry-run" in args          # 预览不改
    also_semi = "--also-semi" in args  # 是否连 semi-auto 一起删

    # ============ 2) 拉取项目下所有 task ============
    st, d = dr.api("GET", f"/tasks?project_id={dr.PROJECT_ID}&page_size=1000")
    tasks = d.get("results", []) if st == 200 else []
    print(f"项目 {dr.PROJECT_ID} 共 {len(tasks)} 个 task")

    # total：全项目各来源计数；to_delete：job_id -> (版本号, 待删的 auto 框列表)
    total = {"auto": 0, "manual": 0, "semi-auto": 0, "other": 0}
    to_delete = {}

    # ============ 3) 遍历每个 task 的每个 job，统计 / 收集待删框 ============
    for t in tasks:
        tid = t["id"]
        name = t["name"]
        jobs = dr.get_jobs(tid)
        for j in jobs:
            jid = j["id"]
            version, shapes = dr.get_job_annotations(jid)   # 取当前版本号+所有框
            if version is None:
                continue
            auto_shapes = []
            tc = {"auto": 0, "manual": 0, "semi-auto": 0, "other": 0}
            for s in shapes:
                src = s.get("source", "")
                if src == "auto":
                    tc["auto"] += 1
                    total["auto"] += 1
                    if not also_semi:
                        auto_shapes.append(s)          # 默认：auto 进待删列表
                elif src == "manual":
                    tc["manual"] += 1
                    total["manual"] += 1
                elif src == "semi-auto":
                    tc["semi-auto"] += 1
                    total["semi-auto"] += 1
                    if also_semi:
                        auto_shapes.append(s)          # 仅当 --also-semi 时才删 semi
                else:
                    tc["other"] += 1
                    total["other"] += 1
            if auto_shapes and not stats_mode:
                to_delete[jid] = (version, auto_shapes)   # 记录待删
            if (dry or stats_mode) and tc["auto"]:
                print(f"  task {tid} {name!r}: auto={tc['auto']} manual={tc['manual']} semi={tc['semi-auto']} other={tc['other']}")

    # ============ 4) 打印来源分布 ============
    print("\n===== 来源分布统计 =====")
    print(f"  auto(待删)     : {total['auto']}")
    print(f"  manual(保留)   : {total['manual']}")
    print(f"  semi-auto(保留): {total['semi-auto']}")
    print(f"  other          : {total['other']}")
    print(f"  保留合计        : {total['manual'] + (0 if also_semi else total['semi-auto'])}")
    if also_semi:
        print("  [注意] --also-semi: semi-auto 也计入待删，仅留纯 manual")

    if stats_mode:
        return   # --stats 只看不动

    if dry:
        print(f"\n[dry-run] 将删除 auto 框的 job 数: {len(to_delete)}")
        return   # --dry-run 只预览

    # ============ 5) 实际删除 ============
    print(f"\n===== 开始删除 auto 框（保留 manual/semi-auto）=====")
    n_jobs = len(to_delete)
    done = 0
    total_del = 0
    for jid, (version, shapes) in to_delete.items():
        st = dr.remove_shapes(jid, shapes, version)   # 分批 PATCH delete，version 自增
        if st == 200:
            done += 1
            total_del += len(shapes)
            print(f"  job {jid}: 删除 {len(shapes)} 个 auto 框 (OK)")
        else:
            print(f"  [错误] job {jid} 删除失败 HTTP {st}")
        import sys as _s
        _s.stdout.flush()   # 每删一个 job 立即刷屏，方便长时间任务看进度
    print(f"完成: 处理 job {done}/{n_jobs}, 删除 auto 框 {total_del}")


if __name__ == "__main__":
    main()
