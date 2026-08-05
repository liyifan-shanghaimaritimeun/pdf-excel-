# 表格检测 YOLO 训练代码（中文注释版）

本目录是「表格 / 表头 / 重点内容 / 型号」4 类目标检测训练流水线的**完整可读副本**，
每个文件都按「代码块 / 函数 / 关键行」加了中文作用说明，方便逐段阅读。

## 一、整体流程（数据如何一步步变成模型）

```
CVAT 标注平台 (Project 2)
        │  export_yolo.py        ← 步骤1：把平台标注导出成 YOLO 格式数据集
        ▼
yolo_dataset/  (images/ + labels/ + data.yaml)
        │  train_yolo.py         ← 步骤2：用 ultralytics 训练 YOLOv8n
        ▼
runs/cvat_tables/weights/best.pt   ← 训练好的权重
        │  ├─ gen_docx.py        ← 步骤3：生成 docx 训练报告
        │  └─ vis_compare.py     ← 步骤4：生成「你的标注 vs 模型预测」对照例图
        ▼
表格检测训练报告.docx + example_vis/*.png
        │  ← 自带回的 weights/table_best.pt + predict_tables.py
        ▼
predict_tables.py -i 样册.pdf -o ./out
        │
        ▼
out/vis/*.png  +  out/detections.json   ← 框好框的可视化图 + 结构化坐标
```

> 备注：`export_yolo.py` 与 `clear_auto.py` 复用了 `cvat_dedup_regen.py` 里的
> 常量（TOKEN / BASE / PROJECT_ID）和几个 API 辅助函数，所以本目录一并附带了它。

## 二、各类别标签含义

| label_id | 名称     | 含义                                   |
|----------|----------|----------------------------------------|
| 1        | 表格     | 整张表格的外框                         |
| 2        | 表头     | 表格第一行（标题行）                   |
| 3        | 重点内容 | 表格内需要特别强调的单元格 / 区块       |
| 4        | 型号     | 产品型号文本（如 CJX2-0910）           |

## 三、各文件作用速查

| 文件                | 作用                                                         |
|---------------------|--------------------------------------------------------------|
| `train_yolo.py`     | 训练主程序：加载权重 → 训练 50 轮 → 验证 → 导出 best.pt      |
| `export_yolo.py`    | 从 CVAT 把所有留存标注导出为 YOLO 数据集（含 train/val 划分）|
| `clear_auto.py`     | 清空自动标注(auto)，只保留人工手动标注(manual/semi-auto)     |
| `gen_docx.py`       | 读取训练产物，生成可阅读的 docx 训练报告                     |
| `vis_compare.py`    | 画对照例图：蓝框=你的标注(GT)，绿/红=模型预测(对/错)         |
| `monitor_progress.py`| 训练时每 30 秒读一次 results.csv，把每轮指标追加到日志       |
| `predict_tables.py` | **新**：拿本目录 weights/ 下的权重，对图/文件夹/PDF 做推理   |
| `weights/`          | **新**：训练好的权重（table_best.pt 24MB + table_high_recall.pt）|
| `weights/模型说明.md`| **新**：权重的实测指标、用法、局限（必读）                  |
| `cvat_dedup_regen.py`| 复用的 CVAT 治理脚本（去重 / 全页重生 / API 辅助函数）       |
| `data.yaml示例.txt` | YOLO 训练所需的 data.yaml 写法示例                           |

## 四、怎么跑（顺序）

1. **清标（可选）**：`python clear_auto.py --dry-run` 先看会删多少，再 `python clear_auto.py`
2. **导出**：`python export_yolo.py` → 生成 `yolo_dataset/`
3. **训练**：`python train_yolo.py` → 生成 `runs/cvat_tables/`，结束自动复制 best.pt
4. **报告**：`python gen_docx.py`
5. **对照图**：`python vis_compare.py`
6. **监视（训练时另开一个终端）**：`python monitor_progress.py`
7. **推理（用训练好的权重跑图/PDF）**：
   ```bash
   python predict_tables.py -i 测试数据/元器件—识别产品型号 -o ./out
   # 想换高召回权重：python predict_tables.py -i 某页.png -w weights/table_high_recall.pt
   ```
   详见 `predict_tables.py` 文件头注释和 `weights/模型说明.md`。

> 所有路径写死在脚本顶部的 `ROOT` 常量里，搬家时需同步修改。
