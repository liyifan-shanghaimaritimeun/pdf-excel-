"""
PDF表格数据提取器 - GUI界面 v2

使用Tkinter构建的图形界面，支持多选PDF文件，提供以下功能：
1. PDF文件选择和浏览（支持多选）
2. 页码范围输入（支持全选、单页、范围）
3. 关键词输入和快捷按钮
4. 表格识别和预览
5. 关键词搜索（单表搜索、全部表格搜索）
6. 搜索进度显示
7. 数据预览和导出Excel
8. 导出所有表格

界面布局：
- 顶部工具栏：文件选择、页码输入、识别表格按钮
- 关键词区域：输入框、快捷按钮
- 表格选择区域：下拉框、预览按钮、搜索按钮、导出按钮
- 进度条区域：进度显示、状态提示
- 操作按钮区域：导出Excel按钮
- 数据预览区域：表格展示、统计信息
"""

import os
import sys
import threading
import queue
import tkinter as tk
import logging
import tempfile
from datetime import datetime
from tkinter import ttk, filedialog, messagebox
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_table_extractor import EnhancedPDFTableExtractor, YOLOTableDetector

# 型号库目录（与本项目脚本同目录下的 model_db）；缺失时 ModelExtractor 静默跳过，无害
MODEL_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_db")

# 配置日志（PyInstaller onefile 临时目录可能只读，文件日志写入系统临时目录并容错）
def _make_log_handlers():
    handlers = [logging.StreamHandler()]
    try:
        if getattr(sys, 'frozen', False):
            log_path = os.path.join(tempfile.gettempdir(), 'PDF表格提取器_v2.log')
        else:
            log_path = 'app.log'
        handlers.insert(0, logging.FileHandler(log_path, encoding='utf-8'))
    except Exception:
        pass
    return handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=_make_log_handlers()
)
logger = logging.getLogger(__name__)


class PDFTableExtractorGUI:
    """
    PDF表格提取器GUI主类 v2

    负责界面初始化、事件处理、搜索逻辑和数据展示，支持多选PDF文件。
    """

    def __init__(self, root):
        """
        初始化GUI界面

        Args:
            root: Tkinter根窗口
        """
        self.root = root
        self.root.title("PDF 表格数据提取器 v2")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)      # 允许自由缩放（配合预览区右下角 Sizegrip）
        self.root.minsize(900, 600)          # 最小尺寸，防止缩太小把预览区挤没

        # 数据状态
        self.current_df = None           # 当前搜索结果DataFrame
        self.pdf_paths = []              # PDF文件路径列表（支持多选）
        self.pdf_page_counts = {}        # 每个PDF文件的页数映射
        self.tables = []                 # 识别到的表格列表
        self.current_table_index = 0     # 当前选中的表格索引
        self.extractors = {}             # 每个PDF文件的提取器实例映射
        self.is_searching = False        # 是否正在搜索
        self.search_queue = queue.Queue()  # 搜索进度消息队列
        
        # 初始化 YOLO 表格检测器（使用 table_1cls_dev.pt 新权重）
        self.yolo_detector = YOLOTableDetector(conf=0.10)
        yolo_ok = self.yolo_detector.load_model()
        if yolo_ok:
            logger.info("✓ YOLO 表格检测器初始化成功（table_1cls_dev.pt）")
        else:
            logger.warning("✗ YOLO 表格检测器初始化失败，将降级使用 find_tables + 布局推断")

        # 本地模型路径（优先使用同目录下的models文件夹）
        self.model_dir = self._find_local_model_dir()

        # 创建界面控件
        self._create_widgets()
        
    def _find_local_model_dir(self):
        """
        查找本地模型目录（使用glob模糊匹配）
        
        按以下顺序查找：
        1. 程序同目录下的models文件夹
        2. 程序同目录下的.paddleocr文件夹
        
        使用glob匹配模型文件夹，支持不同版本的模型命名：
        - ch_PP-OCRv4_det_infer / ch_PP-OCRv3_det_infer / ch_PP-OCRv5_det_infer
        - ch_PP-OCRv4_rec_infer / ch_PP-OCRv3_rec_infer / ch_PP-OCRv5_rec_infer
        
        Returns:
            模型目录路径，如果未找到则返回None
        """
        import glob
        
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        
        # 检查程序同目录下的models文件夹（使用glob递归模糊匹配）
        models_dir = os.path.join(exe_dir, 'models')
        if os.path.isdir(models_dir):
            det_pattern = os.path.join(models_dir, '**', '*_det_infer', 'inference.pdmodel')
            rec_pattern = os.path.join(models_dir, '**', '*_rec_infer', 'inference.pdmodel')
            
            det_models = glob.glob(det_pattern, recursive=True)
            rec_models = glob.glob(rec_pattern, recursive=True)
            
            if det_models and rec_models:
                return models_dir
        
        # 检查程序同目录下的.paddleocr文件夹
        paddleocr_dir = os.path.join(exe_dir, '.paddleocr')
        if os.path.isdir(paddleocr_dir):
            return paddleocr_dir
        
        return None

    def _create_widgets(self):
        """创建所有界面控件"""
        # Treeview 样式：让列边框/表头分隔线可见，支持拖动调列宽
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('Treeview', rowheight=28, borderwidth=1, relief='solid')
        style.configure('Treeview.Heading', borderwidth=1, relief='solid', padding=(6, 4))
        style.map('Treeview.Heading',
                  background=[('active', '#e0e0e0')],
                  relief=[('active', 'solid'), ('!active', 'solid')])
        style.configure('Treeview.Separator', background='#b0b0b0')

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 工具栏区域 ==========
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, pady=5)

        # PDF文件选择（支持多选）
        ttk.Label(toolbar_frame, text="PDF 文件:").pack(side=tk.LEFT, padx=5)
        self.pdf_path_var = tk.StringVar()
        pdf_entry = ttk.Entry(toolbar_frame, textvariable=self.pdf_path_var, width=60)
        pdf_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="浏览", command=self._browse_pdf).pack(side=tk.LEFT, padx=5)

        # 页码输入
        page_frame = ttk.Frame(toolbar_frame)
        page_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(page_frame, text="页码:").pack(side=tk.LEFT, padx=5)
        self.page_range_var = tk.StringVar(value="全选")
        page_entry = ttk.Entry(page_frame, textvariable=self.page_range_var, width=10)
        page_entry.pack(side=tk.LEFT, padx=5)

        # 识别表格/取消按钮
        self.extract_button = ttk.Button(toolbar_frame, text="识别表格", command=self._extract_or_cancel)
        self.extract_button.pack(side=tk.RIGHT, padx=5)

        # ========== 型号搜索区域（新增） ==========
        model_search_frame = ttk.LabelFrame(main_frame, text="型号搜索（输入特征如 MWIC）", padding="10")
        model_search_frame.pack(fill=tk.X, pady=5)

        model_search_input_frame = ttk.Frame(model_search_frame)
        model_search_input_frame.pack(fill=tk.X)

        ttk.Label(model_search_input_frame, text="型号特征:").pack(side=tk.LEFT, padx=5)
        self.model_search_var = tk.StringVar()
        self.model_search_entry = ttk.Entry(model_search_input_frame, textvariable=self.model_search_var, width=30)
        self.model_search_entry.pack(side=tk.LEFT, padx=5)
        self.model_search_entry.bind('<Return>', lambda e: self._search_models())

        ttk.Button(model_search_input_frame, text="搜索型号", command=self._search_models).pack(side=tk.LEFT, padx=5)
        ttk.Button(model_search_input_frame, text="清除结果", command=self._clear_model_results).pack(side=tk.LEFT, padx=5)

        # 型号搜索结果统计
        self.model_search_stats = ttk.Label(model_search_frame, text="")
        self.model_search_stats.pack(anchor=tk.W, pady=3)

        # 型号搜索结果
        self.model_result_text = tk.Text(model_search_frame, height=3, wrap=tk.WORD)
        self.model_result_text.pack(fill=tk.X, pady=3)
        self.model_result_text.config(state=tk.DISABLED)

        # ========== 关键词搜索区域 ==========
        keyword_frame = ttk.LabelFrame(main_frame, text="表头关键词搜索（逗号分隔）", padding="10")
        keyword_frame.pack(fill=tk.X, pady=5)

        ttk.Label(keyword_frame, text="输入表头关键词，如 partnumber, cap, wv:").pack(anchor=tk.W)
        self.keywords_text = tk.Text(keyword_frame, height=2, wrap=tk.WORD)
        self.keywords_text.pack(fill=tk.X, pady=5)
        self.keywords_text.insert(tk.END, "partnumber")

        # 常用关键词快捷按钮
        common_keywords_frame = ttk.Frame(keyword_frame)
        common_keywords_frame.pack(fill=tk.X, pady=5)

        common_keywords = [
            "partnumber", "cap", "wv", "size", "tolerance",
            "型号", "电容量", "额定电压", "尺寸", "公差"
        ]

        for kw in common_keywords:
            ttk.Button(common_keywords_frame, text=kw,
                       command=lambda k=kw: self._add_keyword(k)).pack(side=tk.LEFT, padx=3)

        # ========== 表格选择区域 ==========
        table_frame = ttk.LabelFrame(main_frame, text="表格选择", padding="10")
        table_frame.pack(fill=tk.X, pady=5)

        # 表格下拉选择框
        self.table_var = tk.StringVar()
        self.table_combobox = ttk.Combobox(table_frame, textvariable=self.table_var, state="readonly")
        self.table_combobox.pack(side=tk.LEFT, padx=5)
        self.table_combobox.bind("<<ComboboxSelected>>", self._on_table_selected)

        # 操作按钮
        ttk.Button(table_frame, text="预览原始表格", command=self._preview_raw_table).pack(side=tk.LEFT, padx=5)
        ttk.Button(table_frame, text="导出选中表格", command=self._export_selected_table).pack(side=tk.LEFT, padx=5)
        ttk.Button(table_frame, text="导出所有表格", command=self._export_all_tables).pack(side=tk.LEFT, padx=5)

        # 搜索按钮组
        search_btn_frame = ttk.Frame(table_frame)
        search_btn_frame.pack(side=tk.RIGHT, padx=5)
        ttk.Button(search_btn_frame, text="单表搜索", command=self._search_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_btn_frame, text="全表搜索", command=self._search_all_pages).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_btn_frame, text="全表模糊搜索", command=self._search_all_fuzzy).pack(side=tk.LEFT, padx=2)

        # ========== 进度条区域 ==========
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.status_label = ttk.Label(progress_frame, text="就绪")
        self.status_label.pack(side=tk.RIGHT, padx=5)

        # ========== 操作按钮区域 ==========
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=5)

        # 删除重复数据复选框
        self.remove_duplicates_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(action_frame, text="删除重复数据", variable=self.remove_duplicates_var).pack(side=tk.RIGHT, padx=5)

        # 导出Excel按钮
        ttk.Button(action_frame, text="导出 Excel", command=self._export_excel).pack(side=tk.RIGHT, padx=5)

        # ========== 数据预览区域 ==========
        preview_frame = ttk.LabelFrame(main_frame, text="数据预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # ---- 预览区改用 grid 布局 ----
        # 原因：pack(side=LEFT, fill=BOTH, expand=True) 会让 Treeview 先占满容器。
        # Treeview 的 requested width = 所有列宽之和，当总列宽 > 容器宽度时（宽表），
        # 后 pack 的滚动条拿不到剩余空间，被压缩成 1x1 像素 —— 越需要横向拖动的宽表
        # 反而越拖不动。grid + weight 可保证滚动条尺寸恒定，与列数无关。
        preview_frame.rowconfigure(0, weight=1)      # 表格行吸收纵向余量
        preview_frame.columnconfigure(0, weight=1)   # 表格列吸收横向余量

        # 表格控件
        self.tree = ttk.Treeview(preview_frame, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")

        # 垂直滚动条（右侧，恒定 17px 宽）
        scrollbar_y = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        # 水平滚动条（底部，恒定满宽）
        scrollbar_x = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=scrollbar_x.set)

        # 右下角缩放手柄：横竖滚动条交汇处，拖动可调整窗口大小
        self.preview_sizegrip = ttk.Sizegrip(preview_frame)
        self.preview_sizegrip.grid(row=1, column=1, sticky="se")

        # 鼠标滚轮支持（垂直滚动 / Shift+滚轮横向滚动）
        self.tree.bind("<MouseWheel>",
                       lambda e: self.tree.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.tree.bind("<Shift-MouseWheel>",
                       lambda e: self.tree.xview_scroll(int(-1 * (e.delta / 120)), "units"))

        # 统计信息标签
        self.stats_label = ttk.Label(preview_frame, text="")
        self.stats_label.grid(row=2, column=0, columnspan=2, pady=5)

    def _browse_pdf(self):
        """
        浏览并选择PDF文件（支持多选）

        弹出文件选择对话框，选择一个或多个PDF文件后初始化提取器并获取文件信息。
        """
        file_paths = filedialog.askopenfilenames(
            title="选择 PDF 文件（可多选）",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_paths:
            self.pdf_paths = list(file_paths)
            self.pdf_page_counts = {}
            self.extractors = {}
            
            # 获取所有PDF文件信息
            total_pages = 0
            total_size = 0
            for file_path in file_paths:
                try:
                    import fitz
                    with fitz.open(file_path) as doc:  # 使用with自动关闭文件
                        page_count = doc.page_count
                        self.pdf_page_counts[file_path] = page_count
                        total_pages += page_count
                    total_size += os.path.getsize(file_path) / (1024 * 1024)
                    
                    # 创建提取器实例（使用新架构 + YOLO 检测）
                    extractor = EnhancedPDFTableExtractor(file_path, use_ocr=True, yolo_detector=self.yolo_detector, model_db_path=MODEL_DB_PATH)
                    self.extractors[file_path] = extractor
                    if extractor.ocr_extractor and extractor.ocr_extractor.ocr:
                        logger.info(f"✓ OCR初始化成功: {os.path.basename(file_path)}")
                    else:
                        logger.warning(f"✗ OCR初始化失败，将在提取时重试: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"文件 {file_path} 处理失败: {e}")
                    self.pdf_page_counts[file_path] = 0

            # 更新显示
            display_text = f"{len(self.pdf_paths)} 个文件"
            self.pdf_path_var.set(display_text)

            messagebox.showinfo("提示", f"已选择 {len(file_paths)} 个 PDF 文件，共 {total_pages} 页，总大小: {total_size:.1f} MB")

    def _add_keyword(self, keyword):
        """
        添加关键词到输入框

        Args:
            keyword: 要添加的关键词
        """
        current_text = self.keywords_text.get("1.0", tk.END).strip()
        if current_text:
            if keyword.lower() not in current_text.lower():
                self.keywords_text.insert(tk.END, f", {keyword}")
        else:
            self.keywords_text.insert(tk.END, keyword)

    def _parse_keywords(self):
        """
        解析关键词输入框

        Returns:
            关键词列表，如果输入为空则弹出警告并返回空列表
        """
        keywords_text = self.keywords_text.get("1.0", tk.END).strip()
        if not keywords_text:
            messagebox.showwarning("警告", "请输入搜索关键词")
            return []
        return [kw.strip() for kw in keywords_text.split(",") if kw.strip()]

    def _parse_page_range(self, total_pages):
        """
        解析页码范围输入

        支持的格式：
        - "全选" 或 "all": 返回所有页码
        - 单个数字（如 "2"）: 返回该页码
        - 范围（如 "1-5"）: 返回起始到结束的所有页码

        Args:
            total_pages: 当前文件的总页数

        Returns:
            页码列表（从0开始）
        """
        page_range = self.page_range_var.get().strip()
        
        if page_range.lower() == "全选" or page_range.lower() == "all":
            if total_pages > 0:
                return list(range(total_pages))
            return [0]
        
        if page_range.isdigit():
            return [int(page_range) - 1]
        
        if "-" in page_range:
            parts = page_range.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start = int(parts[0]) - 1
                end = int(parts[1]) - 1
                return list(range(max(0, start), min(total_pages, end + 1)))
        
        return [0]

    def _extract_or_cancel(self):
        """
        提取表格或取消提取的切换方法
        
        如果正在提取，则取消提取；否则开始提取。
        """
        if hasattr(self, 'is_extracting') and self.is_extracting:
            self._cancel_extract()
        else:
            self._extract_tables()
    
    def _cancel_extract(self):
        """
        取消正在进行的表格提取操作
        """
        self.is_extracting = False
        self.status_label.config(text="正在取消...")
        self.extract_button.config(text="识别表格")
    
    def _extract_tables(self):
        """
        提取PDF中的表格（支持多文件，后台线程执行）

        根据页码范围，在指定页面中识别表格并显示在下拉框中。
        支持从多个PDF文件中提取表格。
        提取完成后自动预览第一个表格。
        """
        if not self.pdf_paths:
            messagebox.showwarning("警告", "请选择 PDF 文件")
            return

        if hasattr(self, 'is_extracting') and self.is_extracting:
            messagebox.showwarning("警告", "正在提取中，请等待完成")
            return

        # 计算总页数
        total_pages = 0
        for file_path in self.pdf_paths:
            total_pages += self.pdf_page_counts.get(file_path, 0)
        
        if total_pages == 0:
            messagebox.showwarning("警告", "无法获取PDF页数")
            return

        self.is_extracting = True
        self.progress_var.set(0)
        self.status_label.config(text="正在提取表格...")
        self.extract_button.config(text="取消")

        # 创建后台线程
        extract_thread = threading.Thread(target=self._extract_worker, args=(total_pages,))
        extract_thread.daemon = True
        extract_thread.start()

        # 启动进度更新
        self._update_extract_progress()

    def _extract_worker(self, total_pages):
        """
        表格提取工作线程

        在后台线程中遍历所有PDF文件和页面，执行表格提取。
        将结果放入queue，由主线程统一更新，避免线程间变量竞争。

        Args:
            total_pages: 总页数
        """
        worker_tables = []
        processed_pages = 0
        
        try:
            logger.info(f"开始提取表格，共 {len(self.pdf_paths)} 个文件，{total_pages} 页")
            
            for file_path in self.pdf_paths:
                if not self.is_extracting or not os.path.exists(file_path):
                    break

                extractor = self.extractors.get(file_path)
                if not extractor:
                    logger.info(f"创建EnhancedPDFTableExtractor: {file_path}")
                    extractor = EnhancedPDFTableExtractor(file_path, use_ocr=True, yolo_detector=self.yolo_detector, model_db_path=MODEL_DB_PATH)
                    self.extractors[file_path] = extractor
                    if extractor.ocr_extractor:
                        if extractor.ocr_extractor.ocr:
                            logger.info("✓ OCR初始化成功")
                        else:
                            logger.warning("✗ OCR实例为None")
                            extractor._init_ocr_if_needed()
                            if extractor.ocr_extractor and extractor.ocr_extractor.ocr:
                                logger.info("✓ 重新初始化OCR成功")
                            else:
                                logger.error("✗ 重新初始化OCR仍然失败")
                    else:
                        logger.warning("✗ OCR提取器未创建")
                
                file_total_pages = self.pdf_page_counts.get(file_path, 0)
                if file_total_pages == 0:
                    try:
                        import fitz
                        with fitz.open(file_path) as doc:  # 使用with自动关闭文件
                            file_total_pages = doc.page_count
                            self.pdf_page_counts[file_path] = file_total_pages
                    except Exception as e:
                        logger.error(f"获取文件页数失败: {file_path}, 错误: {e}")
                        continue

                page_nums = self._parse_page_range(file_total_pages)

                for page_num in page_nums:
                    if not self.is_extracting or page_num >= file_total_pages:
                        break
                    processed_pages += 1
                    try:
                        page_tables = extractor.extract_tables(page_num)
                        for table in page_tables:
                            table_info = {
                                "data": table,
                                "page_num": page_num,
                                "file_path": file_path
                            }
                            worker_tables.append(table_info)
                    except Exception as e:
                        logger.error(f"处理文件 {file_path} 第{page_num+1}页时出错: {e}")

                    # 更新进度
                    progress = (processed_pages / total_pages) * 100
                    self.search_queue.put(("extract_progress", progress))
                    self.search_queue.put(("extract_count", len(worker_tables)))

            logger.info(f"表格提取完成，共识别到 {len(worker_tables)} 个表格")

            # ===== 表外型号汇总：作为最后一个"表格"集中展示 =====
            # 表外型号 = 不在任何表格框内、由全页文本/OCR 正则命中的型号
            # （产品图旁、封底、纯文字页等）。只读提取器缓存，不触发重新提取。
            summary_table = self._build_out_table_model_summary()
            if summary_table:
                worker_tables.append(summary_table)

            # 将结果放入queue，由主线程统一更新
            self.search_queue.put(("extract_done", worker_tables))

        except Exception as e:
            logger.error(f"表格提取线程出错: {e}", exc_info=True)
            self.search_queue.put(("extract_error", str(e)))

    def _build_out_table_model_summary(self):
        """
        汇总所有文件的「表外型号」，构造成一个虚拟表格（追加到表格列表末尾）

        数据来源：各 extractor 的 _scanned_cache（只读，不重新提取）。
        表内型号不在此列——它们已经在各自表格里。

        Returns:
            table_info 字典（含 is_model_summary=True），无型号时返回 None
        """
        header = ["序号", "型号", "类型", "置信度", "类别", "厂商", "来源文件", "页码", "上下文"]
        rows = [header]
        seen = set()

        for file_path in self.pdf_paths:
            extractor = self.extractors.get(file_path)
            if not extractor or not hasattr(extractor, "get_cached_out_table_models"):
                continue
            file_name = os.path.basename(file_path)
            # 型号库反查接口（命中库可返回 type/company/category）
            model_extractor = getattr(extractor, "model_extractor", None)
            try:
                for m in extractor.get_cached_out_table_models():
                    model = str(m.get("model", "")).strip()
                    if not model:
                        continue
                    page_num = m.get("page", 0)
                    key = (file_name, page_num, m.get("model_upper") or model.upper())
                    if key in seen:
                        continue
                    seen.add(key)
                    # 参数反查（型号库已加载才有效；未加载返回未收录）
                    if model_extractor is not None:
                        params = model_extractor.get_model_params(model)
                        type_ = params.get("type", "")
                        company_ = params.get("company", "")
                    else:
                        type_ = ""
                        company_ = ""
                    rows.append([
                        str(len(rows)),
                        model,
                        str(m.get("pattern_type", "")),
                        str(m.get("confidence", "")),
                        str(type_),
                        str(company_),
                        file_name,
                        str(int(page_num) + 1),
                        str(m.get("context", "")),
                    ])
            except Exception as e:
                logger.error(f"汇总表外型号失败 {file_name}: {e}")

        if len(rows) <= 1:
            logger.info("表外型号汇总：未发现表外型号")
            return None

        logger.info(f"表外型号汇总：共 {len(rows) - 1} 个")
        return {
            "data": rows,
            "page_num": -1,
            "file_path": "",
            "is_model_summary": True,
        }

    def _update_extract_progress(self):
        """
        更新表格提取进度

        从消息队列中读取进度信息并更新界面显示。
        """
        if not self.is_extracting and self.search_queue.empty():
            return

        try:
            while not self.search_queue.empty():
                msg_type, msg_data = self.search_queue.get_nowait()

                if msg_type == "extract_progress":
                    self.progress_var.set(msg_data)
                    self.status_label.config(text=f"正在提取... {int(msg_data)}%")
                elif msg_type == "extract_count":
                    self.status_label.config(text=f"已识别 {msg_data} 个表格")
                elif msg_type == "extract_done":
                    self.is_extracting = False
                    self.progress_var.set(100)
                    self.status_label.config(text="提取完成")
                    self.extract_button.config(text="识别表格")
                    
                    # 从queue接收结果，避免线程间变量竞争
                    self.tables = msg_data
                    
                    if not self.tables:
                        messagebox.showinfo("提示", "未识别到表格")
                        self.table_combobox["values"] = []
                    else:
                        table_options = []
                        for i, table_info in enumerate(self.tables):
                            table = table_info["data"]
                            cols = len(table[0]) if table else 0
                            rows = len(table)
                            if table_info.get("is_model_summary"):
                                # 表外型号汇总（虚拟表，恒在最后）
                                table_options.append(f"表格 {i+1} | ★ 表外型号汇总 | 共 {rows - 1} 个型号")
                                continue
                            file_name = os.path.basename(table_info["file_path"])
                            page_display = self._display_page_with_physical(table_info)
                            table_options.append(f"表格 {i+1} | {file_name} | {page_display} | {rows}行x{cols}列")

                        self.table_combobox["values"] = table_options
                        self.table_var.set(table_options[0])
                        self.current_table_index = 0

                        messagebox.showinfo("成功", f"从 {len(self.pdf_paths)} 个文件中识别到 {len(self.tables)} 个表格")
                        self._preview_raw_table()
                    return
                elif msg_type == "extract_error":
                    self.is_extracting = False
                    self.status_label.config(text="提取失败")
                    self.extract_button.config(text="识别表格")
                    messagebox.showerror("错误", f"提取失败: {msg_data}")
                    return

        except queue.Empty:
            pass

        # 继续监听消息队列
        self.root.after(100, self._update_extract_progress)

    def _on_table_selected(self, event):
        """
        表格选择事件处理

        当用户从下拉框选择表格时，更新当前表格索引并预览该表格。

        Args:
            event: 事件对象
        """
        selected = self.table_var.get()
        if selected:
            for i, option in enumerate(self.table_combobox["values"]):
                if option == selected:
                    self.current_table_index = i
                    self._preview_raw_table()
                    break

    def _display_page_label(self, table_info: dict) -> str:
        """
        返回表格所在页的PDF实际页码标签（如 '1'、'i'、'A-3'）。
        优先使用PDF的get_page_label()获取实际页码，若无法获取则回退到物理页码+1。
        """
        # 表外型号汇总是跨页虚拟表，没有单一页码
        if table_info.get("is_model_summary"):
            return "-"
        page_num = table_info.get("page_num", 0)
        file_path = table_info.get("file_path", "")
        extractor = self.extractors.get(file_path)
        try:
            if extractor and hasattr(extractor, 'get_page_label'):
                label = extractor.get_page_label(page_num)
                if label and str(label).strip():
                    return str(label)
        except Exception:
            pass
        # 回退：物理页码+1（从1开始）
        return str(page_num + 1)

    def _display_page_with_physical(self, table_info: dict) -> str:
        """
        返回表格所在页的PDF页码标签，包含物理页码信息。
        格式: "实际页码(物理页N)"
        """
        if table_info.get("is_model_summary"):
            return "-"
        page_num = table_info.get("page_num", 0)
        page_label = self._display_page_label(table_info)
        if page_label != str(page_num + 1):
            return f"{page_label}(物理页{page_num + 1})"
        return page_label

    def _preview_raw_table(self):
        """
        预览原始表格

        在主界面底部预览框中显示原始表格，支持横向拖动查看右边内容。
        """
        if not self.tables or self.current_table_index >= len(self.tables):
            return

        table_info = self.tables[self.current_table_index]
        table = table_info["data"]
        page_label = self._display_page_label(table_info)
        file_name = os.path.basename(table_info.get("file_path", ""))

        # 清空现有内容
        for item in self.tree.get_children():
            self.tree.delete(item)
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        self.tree["columns"] = ()

        if not table:
            self.stats_label.config(text=f"{file_name} - 第{page_label}页: 空表格")
            return

        # 识别表头行并合并
        columns = [str(i) for i in range(len(table[0]))]
        self.tree["columns"] = columns

        # 获取对应的提取器
        file_path = table_info.get("file_path", "")
        extractor = self.extractors.get(file_path)

        if extractor and hasattr(extractor, 'keyword_searcher') and extractor.keyword_searcher:
            start_row, end_row = extractor.keyword_searcher.find_header_rows(table)
            merged_header = extractor.keyword_searcher.build_merged_header(table, start_row, end_row)
        else:
            start_row, end_row = 0, 0
            merged_header = [str(cell).strip() for cell in table[0]]

        # 设置列标题和宽度（stretch=False 允许横向拖动）
        num_cols = len(table[0])
        col_width = max(150, min(250, int(1200 / max(num_cols, 1))))
        for i in range(num_cols):
            header_text = merged_header[i][:30] + "..." if len(merged_header[i]) > 30 else merged_header[i]
            self.tree.heading(str(i), text=f"列{i+1}: {header_text}")
            self.tree.column(str(i), width=col_width, minwidth=100, stretch=False)

        # 插入表格数据
        for idx, row in enumerate(table):
            values = []
            for cell in row:
                cell_str = str(cell)[:80] + "..." if len(str(cell)) > 80 else str(cell)
                values.append(cell_str)

            # 表头行添加高亮标签
            tag = "header" if start_row <= idx <= end_row else ""
            self.tree.insert("", tk.END, values=values, tags=(tag,))

        # 添加表头行样式
        self.tree.tag_configure("header", background="#D3D3D3", font=('Arial', 10, 'bold'))

        # 更新统计信息
        if table_info.get("is_model_summary"):
            self.stats_label.config(
                text=f"★ 表外型号汇总（不在任何表格内的型号）| 共 {len(table) - 1} 个型号，跨全部已提取页面"
            )
        else:
            self.stats_label.config(text=f"{file_name} | 第{page_label}页 (PDF实际页码) | 共 {len(table)} 行 x {len(table[0])} 列")

    def _search_data(self):
        """
        单表搜索：在当前选中的表格中精准搜索关键词

        在当前选中的单个表格中，使用精准匹配方式查找表头中包含关键词的列，
        然后提取这些匹配列的所有内容。仅搜索当前选中的单个表格。
        """
        if not self.tables or self.current_table_index >= len(self.tables):
            messagebox.showwarning("警告", "请先识别表格并选择要搜索的表格")
            return

        keywords = self._parse_keywords()
        if not keywords:
            return

        table_info = self.tables[self.current_table_index]
        table = table_info["data"]
        page_label = self._display_page_label(table_info)
        file_path = table_info.get("file_path", "")
        file_name = os.path.basename(file_path)

        try:
            all_data = []

            # 获取对应的提取器
            extractor = self.extractors.get(file_path)

            if extractor and hasattr(extractor, 'keyword_searcher') and extractor.keyword_searcher:
                # 识别表头行
                start_row, end_row = extractor.keyword_searcher.find_header_rows(table)
                merged_header = extractor.keyword_searcher.build_merged_header(table, start_row, end_row)

                # 精准匹配：使用提取器的 search_all_headers 方法
                header_mapping = extractor.keyword_searcher.search_all_headers(table, keywords)

                if header_mapping:
                    # 提取匹配列的数据
                    for row_idx, row in enumerate(table):
                        if row_idx < start_row:
                            continue

                        row_data = {}
                        for keyword, col_idx in header_mapping.items():
                            if col_idx < len(row):
                                cell_value = str(row[col_idx]).strip()
                                row_data[keyword] = cell_value

                        if row_data and any(str(v).strip() for v in row_data.values()):
                            row_data["_页码"] = page_label
                            row_data["_来源表格"] = f"表格{self.current_table_index+1}"
                            row_data["_来源文件"] = file_name
                            all_data.append(row_data)
            else:
                # 降级处理
                start_row, end_row = 0, 0
                merged_header = [str(cell).strip() if cell else f"列{c+1}" for c, cell in enumerate(table[0])]
                header_mapping = {}
                for col_idx, header in enumerate(merged_header):
                    for kw in keywords:
                        if kw.lower() == str(header).lower():
                            header_mapping[kw] = col_idx
                            break
                if header_mapping:
                    for row_idx, row in enumerate(table):
                        if row_idx == 0:
                            continue
                        row_data = {}
                        for keyword, col_idx in header_mapping.items():
                            if col_idx < len(row):
                                row_data[keyword] = str(row[col_idx]).strip()
                        if row_data and any(str(v).strip() for v in row_data.values()):
                            row_data["_页码"] = page_label
                            row_data["_来源表格"] = f"表格{self.current_table_index+1}"
                            row_data["_来源文件"] = file_name
                            all_data.append(row_data)

            if all_data:
                self.current_df = pd.DataFrame(all_data)
                self._display_search_results(self.current_df)
                messagebox.showinfo("单表搜索完成", f"找到 {len(all_data)} 条匹配记录")
            else:
                messagebox.showinfo("单表搜索完成", "未找到匹配的表头列")

        except Exception as e:
            messagebox.showerror("搜索失败", f"单表搜索失败: {str(e)}")

    def _search_all_fuzzy(self):
        """
        全表模糊搜索：在所有识别到的表格中模糊匹配表头并提取列内容

        与全表搜索的区别在于表头匹配方式为模糊包含：
        如搜索"芯片"，会匹配到"芯片型号"、"芯片类型"等包含"芯片"的表头，
        然后提取这些匹配列的所有内容。搜索过程中显示进度条。
        """
        if not self.tables:
            messagebox.showwarning("警告", "请先识别表格")
            return

        keywords = self._parse_keywords()
        if not keywords:
            return

        self.is_searching = True
        self.progress_var.set(0)
        self.status_label.config(text="正在全表模糊搜索...")

        # 创建搜索线程
        search_thread = threading.Thread(target=self._search_fuzzy_worker, args=(keywords,))
        search_thread.daemon = True
        search_thread.start()

        # 启动进度更新
        self._update_search_progress()

    def _search_fuzzy_worker(self, keywords):
        """
        全表模糊搜索工作线程

        在后台线程中遍历所有表格，模糊匹配表头（关键词包含于表头），
        找到匹配列后提取该列的所有数据。

        Args:
            keywords: 关键词列表
        """
        all_data = []
        total_tables = len(self.tables)

        logger.info(f"开始全表模糊搜索关键词: {keywords}, 共 {total_tables} 个表格")

        for i, table_info in enumerate(self.tables):
            if not self.is_searching:
                break

            table = table_info["data"]
            page_label = self._display_page_label(table_info)
            file_path = table_info.get("file_path", "")
            file_name = os.path.basename(file_path)

            try:
                # 获取表头信息
                extractor = self.extractors.get(file_path)
                if extractor and hasattr(extractor, 'keyword_searcher') and extractor.keyword_searcher:
                    start_row, end_row = extractor.keyword_searcher.find_header_rows(table)
                    merged_header = extractor.keyword_searcher.build_merged_header(table, start_row, end_row)
                else:
                    start_row, end_row = 0, 0
                    merged_header = [str(cell).strip() if cell else f"列{c+1}" for c, cell in enumerate(table[0])]

                # 模糊匹配：找出表头中包含关键词的列
                header_mapping = {}  # {显示用关键词: 列索引}
                for col_idx, header in enumerate(merged_header):
                    header_lower = str(header).lower()
                    for kw in keywords:
                        kw_lower = kw.lower()
                        # 模糊包含：关键词出现在表头中，或者表头出现在关键词中
                        if kw_lower in header_lower or header_lower in kw_lower:
                            display_key = f"{kw}({header})" if header_lower != kw_lower else kw
                            if display_key not in header_mapping:
                                header_mapping[display_key] = col_idx
                            break

                if header_mapping:
                    # 提取匹配列的数据
                    for row_idx, row in enumerate(table):
                        if row_idx < start_row:
                            continue

                        row_data = {}
                        has_value = False
                        for display_key, col_idx in header_mapping.items():
                            if col_idx < len(row):
                                cell_value = str(row[col_idx]).strip()
                                row_data[display_key] = cell_value
                                if cell_value:
                                    has_value = True

                        if row_data and has_value:
                            row_data["_页码"] = page_label
                            row_data["_来源表格"] = f"表格{i+1}"
                            row_data["_来源文件"] = file_name
                            all_data.append(row_data)

            except Exception as e:
                logger.error(f"处理表格{i+1}时出错: {e}")

            # 更新进度
            progress = ((i + 1) / total_tables) * 100
            self.search_queue.put(("progress", progress))
            self.search_queue.put(("count", len(all_data)))

        logger.info(f"全表模糊搜索完成，共找到 {len(all_data)} 条记录")
        self.search_queue.put(("fuzzy_done", all_data))

    def _search_all_pages(self):
        """
        全表搜索：在所有识别到的表格中精准搜索关键词

        在所有已识别的表格中查找包含关键词的列，并将结果显示在预览区域。
        使用表头精准匹配（关键词需与列表头匹配），搜索过程中显示进度条。
        """
        if not self.tables:
            messagebox.showwarning("警告", "请先识别表格")
            return

        keywords = self._parse_keywords()
        if not keywords:
            return

        self.is_searching = True
        self.progress_var.set(0)
        self.status_label.config(text="正在搜索...")

        # 创建搜索线程
        search_thread = threading.Thread(target=self._search_worker, args=(keywords,))
        search_thread.daemon = True
        search_thread.start()

        # 启动进度更新
        self._update_search_progress()

    def _search_worker(self, keywords):
        """
        搜索工作线程

        在后台线程中遍历所有表格，执行关键词搜索。

        Args:
            keywords: 关键词列表
        """
        all_data = []
        total_tables = len(self.tables)
        
        logger.info(f"开始搜索关键词: {keywords}, 共 {total_tables} 个表格")

        for i, table_info in enumerate(self.tables):
            if not self.is_searching:
                break

            table = table_info["data"]
            page_num = table_info["page_num"]
            file_path = table_info.get("file_path", "")
            page_label = self._display_page_label(table_info)

            # 获取对应的提取器
            extractor = self.extractors.get(file_path)

            try:
                if extractor and hasattr(extractor, 'keyword_searcher') and extractor.keyword_searcher:
                    # 识别表头行
                    start_row, end_row = extractor.keyword_searcher.find_header_rows(table)
                    
                    # 搜索关键词对应的列
                    header_mapping = extractor.keyword_searcher.search_all_headers(table, keywords)
                    
                    if header_mapping:
                        # 提取表头行和数据行
                        for row_idx, row in enumerate(table):
                            if row_idx < start_row:
                                continue
                            
                            row_data = {}
                            for keyword, col_idx in header_mapping.items():
                                if col_idx < len(row):
                                    row_data[keyword] = row[col_idx]
                            
                            if row_data:
                                row_data["_页码"] = page_label
                                row_data["_来源表格"] = f"表格{i+1}"
                                row_data["_来源文件"] = os.path.basename(file_path)
                                all_data.append(row_data)
                else:
                    # 降级处理：简单搜索
                    for row in table[1:]:
                        row_data = {}
                        for cell in row:
                            for kw in keywords:
                                if kw.lower() in str(cell).lower():
                                    row_data[kw] = cell
                        if row_data:
                            row_data["_页码"] = page_label
                            row_data["_来源表格"] = f"表格{i+1}"
                            row_data["_来源文件"] = os.path.basename(file_path)
                            all_data.append(row_data)
            except Exception as e:
                logger.error(f"处理表格{i+1}时出错: {e}")

            # 更新进度
            progress = ((i + 1) / total_tables) * 100
            self.search_queue.put(("progress", progress))
            self.search_queue.put(("count", len(all_data)))

        logger.info(f"搜索完成，共找到 {len(all_data)} 条记录")
        self.search_queue.put(("done", all_data))

    def _update_search_progress(self):
        """
        更新搜索进度

        从消息队列中读取进度信息并更新界面显示。
        """
        if not self.is_searching and self.search_queue.empty():
            return

        try:
            while not self.search_queue.empty():
                msg_type, msg_data = self.search_queue.get_nowait()

                if msg_type == "progress":
                    self.progress_var.set(msg_data)
                    self.status_label.config(text=f"正在搜索... {int(msg_data)}%")
                elif msg_type == "count":
                    self.status_label.config(text=f"找到 {msg_data} 条记录")
                elif msg_type == "done":
                    self.is_searching = False
                    self.progress_var.set(100)
                    self.status_label.config(text="搜索完成")

                    if msg_data:
                        self.current_df = pd.DataFrame(msg_data)
                        self._display_search_results(self.current_df)
                    else:
                        self.current_df = None
                        messagebox.showinfo("搜索完成", "未找到匹配记录")
                    return
                elif msg_type == "fuzzy_done":
                    self.is_searching = False
                    self.progress_var.set(100)
                    self.status_label.config(text="全表模糊搜索完成")

                    if msg_data:
                        self.current_df = pd.DataFrame(msg_data)
                        self._display_search_results(self.current_df)
                    else:
                        self.current_df = None
                        messagebox.showinfo("全表模糊搜索完成", "未找到匹配的表头列")
                    return

        except queue.Empty:
            pass

        # 继续监听消息队列
        self.root.after(100, self._update_search_progress)

    def _display_search_results(self, df):
        """
        显示搜索结果

        将搜索结果DataFrame显示在预览区域的表格控件中。

        Args:
            df: 搜索结果DataFrame
        """
        # 清空现有表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 设置列
        self.tree["columns"] = list(df.columns)

        # 设置列标题
        for col in df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, minwidth=80, stretch=False)

        # 插入数据（最多显示1000行）
        displayed_rows = 0
        for _, row in df.iterrows():
            if displayed_rows >= 1000:
                break
            values = [str(row[col]) for col in df.columns]
            self.tree.insert("", tk.END, values=values)
            displayed_rows += 1

        # 更新统计信息
        if len(df) > 1000:
            self.stats_label.config(text=f"共 {len(df)} 行, 显示前 1000 行")
        else:
            self.stats_label.config(text=f"共 {len(df)} 行")

    def _display_fuzzy_search_results(self, matched_rows):
        """
        在主界面预览框中显示全表模糊搜索结果

        Args:
            matched_rows: 匹配的行数据列表
        """
        # 清空现有内容
        for item in self.tree.get_children():
            self.tree.delete(item)
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        self.tree["columns"] = ()

        if not matched_rows:
            self.stats_label.config(text="全表模糊搜索: 无匹配结果")
            return

        # 获取所有列名
        columns = list(matched_rows[0].keys())
        self.tree["columns"] = columns

        # 设置列标题
        for col in columns:
            if col.startswith("_"):
                display_name = col[1:]  # 去掉下划线
                width = 100
                anchor = "center"
            else:
                display_name = col
                width = max(120, min(200, int(1000 / max(len(columns), 1))))
                anchor = "w"
            self.tree.heading(col, text=display_name)
            self.tree.column(col, width=width, minwidth=80, stretch=False, anchor=anchor)

        # 插入数据（最多显示1000行）
        displayed_rows = 0
        for row_data in matched_rows:
            if displayed_rows >= 1000:
                break
            values = [str(row_data.get(col, "")) for col in columns]
            self.tree.insert("", tk.END, values=values)
            displayed_rows += 1

        # 更新统计信息
        if len(matched_rows) > 1000:
            self.stats_label.config(text=f"全表模糊搜索 | 共 {len(matched_rows)} 行匹配, 显示前 1000 行")
        else:
            self.stats_label.config(text=f"全表模糊搜索 | 共 {len(matched_rows)} 行匹配")

    def _export_selected_table(self):
        """
        导出选中的原始表格

        将当前选中的表格（在表格选择下拉框中选择的表格）导出为Excel文件。
        包含完整的表头和数据行，保留原始表格结构。
        """
        if not self.tables or self.current_table_index >= len(self.tables):
            messagebox.showwarning("警告", "请先识别表格并选择要导出的表格")
            return

        # 获取选中的表格数据
        table_info = self.tables[self.current_table_index]
        table_data = table_info["data"]
        page_num = table_info["page_num"]
        page_label = self._display_page_label(table_info)
        file_path_info = table_info.get("file_path", "")
        file_name = os.path.basename(file_path_info) if file_path_info else ""

        # 如果表格为空，提示用户
        if not table_data or len(table_data) < 2:
            messagebox.showwarning("警告", "选中的表格数据为空")
            return

        # 识别表头行并合并
        extractor = self.extractors.get(file_path_info)
        if extractor and hasattr(extractor, 'keyword_searcher') and extractor.keyword_searcher:
            start_row, end_row = extractor.keyword_searcher.find_header_rows(table_data)
            merged_header = extractor.keyword_searcher.build_merged_header(table_data, start_row, end_row)
        else:
            merged_header = [str(cell).strip() for cell in table_data[0]]

        # 创建DataFrame（导出完整表格，包含表头行）
        df = pd.DataFrame(table_data, columns=merged_header)

        # 添加来源信息列
        df["_来源文件"] = file_name
        df["_来源页码"] = page_label
        df["_来源表格"] = self.current_table_index + 1

        # 弹出保存对话框
        initial_name = f"表格{self.current_table_index + 1}_{os.path.splitext(file_name)[0]}_第{page_label}页.xlsx" if file_name else f"表格{self.current_table_index + 1}_第{page_label}页.xlsx"
        file_path = filedialog.asksaveasfilename(
            title="保存选中表格 - Excel 文件",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
            initialfile=initial_name
        )

        if file_path:
            try:
                # 导出DataFrame到Excel
                df.to_excel(file_path, index=False, engine="openpyxl")
                messagebox.showinfo("成功", f"Excel 文件已保存到:\n{file_path}")
                if messagebox.askyesno("提示", "是否打开导出的 Excel 文件？"):
                    os.startfile(file_path)
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")

    def _search_models(self):
        """
        在全页OCR文字和表格数据中搜索型号特征
        """
        search_text = self.model_search_var.get().strip()
        if not search_text:
            messagebox.showwarning("提示", "请输入型号特征")
            return
        
        if not self.tables and not self.extractors:
            messagebox.showwarning("提示", "请先识别表格")
            return
        
        search_text_upper = search_text.upper()
        results = []
        
        # 1. 在表格数据中搜索
        for table_idx, table_info in enumerate(self.tables):
            table_data = table_info.get('data', [])
            pdf_file = table_info.get('pdf_file', '未知PDF')
            page_num = table_info.get('page_num', -1)
            
            for row_idx, row in enumerate(table_data):
                for col_idx, cell in enumerate(row):
                    cell_text = str(cell).strip()
                    if search_text_upper in cell_text.upper():
                        results.append({
                            'source': '表格',
                            'pdf': pdf_file,
                            'page': page_num + 1 if page_num >= 0 else '?',
                            'table': table_idx + 1,
                            'row': row_idx + 1,
                            'col': col_idx + 1,
                            'text': cell_text[:100],
                        })
        
        # 2. 在全页OCR文字中搜索（如果有提取器）
        for pdf_path, extractor in self.extractors.items():
            try:
                for page_num in range(len(self.pdf_page_counts.get(pdf_path, []) or [0])):
                    pass  # 页码信息在提取时获取
            except Exception:
                pass
        
        # 显示结果
        self._display_model_results(results, search_text)
    
    def _display_model_results(self, results, search_text):
        """
        显示型号搜索结果
        """
        self.model_result_text.config(state=tk.NORMAL)
        self.model_result_text.delete('1.0', tk.END)
        
        if not results:
            self.model_result_text.insert(tk.END, f"未找到包含 '{search_text}' 的内容")
            self.model_search_stats.config(text="")
        else:
            # 统计
            pdf_count = len(set(r['pdf'] for r in results))
            page_count = len(set((r['pdf'], r['page']) for r in results))
            table_count = len(set((r['pdf'], r['table']) for r in results))
            
            stats = f"找到 {len(results)} 个匹配项 | {pdf_count} 个PDF | {page_count} 个页面 | {table_count} 个表格"
            self.model_search_stats.config(text=stats)
            
            # 显示前20条结果
            display_text = f"搜索 '{search_text}' 共 {len(results)} 个匹配项:\n"
            for i, r in enumerate(results[:20]):
                display_text += f"  [{i+1}] {r['source']} | {r['pdf']} 第{r['page']}页 表{r['table']} 行{r['row']} 列{r['col']}: {r['text']}\n"
            
            if len(results) > 20:
                display_text += f"  ... 还有 {len(results) - 20} 个结果\n"
            
            self.model_result_text.insert(tk.END, display_text)
        
        self.model_result_text.config(state=tk.DISABLED)
    
    def _clear_model_results(self):
        """
        清除型号搜索结果
        """
        self.model_search_var.set("")
        self.model_result_text.config(state=tk.NORMAL)
        self.model_result_text.delete('1.0', tk.END)
        self.model_result_text.config(state=tk.DISABLED)
        self.model_search_stats.config(text="")

    def _export_all_tables(self):
        """
        导出所有识别到的表格到一个Excel文件，每个表格作为单独的sheet页（支持多文件）
        
        大数据量导出时使用后台线程，避免GUI卡死。
        """
        if not self.tables:
            messagebox.showwarning("警告", "请先识别表格")
            return

        # 弹出保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存所有表格 - Excel 文件",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
            initialfile="所有表格.xlsx"
        )

        if file_path:
            self.is_exporting = True
            self.progress_var.set(0)
            self.status_label.config(text="正在导出...")
            
            # 创建导出线程
            export_thread = threading.Thread(target=self._export_all_tables_worker, args=(file_path,))
            export_thread.daemon = True
            export_thread.start()
            
            # 启动进度更新
            self._update_export_progress()
    
    def _export_all_tables_worker(self, file_path):
        """
        导出所有表格的工作线程（含型号统计汇总）
        
        Args:
            file_path: 保存文件路径
        """
        try:
            total_tables = len(self.tables)
            model_stats_data = []  # 型号统计数据
            
            # 创建Excel写入器
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                for idx, table_info in enumerate(self.tables):
                    table_data = table_info["data"]
                    page_num = table_info["page_num"]
                    page_label = self._display_page_label(table_info)
                    file_path_info = table_info.get("file_path", "")
                    file_name = os.path.basename(file_path_info) if file_path_info else ""
                    is_summary = table_info.get("is_model_summary", False)

                    if not table_data or len(table_data) < 2:
                        continue

                    # 识别表头行并合并
                    extractor = self.extractors.get(file_path_info)
                    if extractor and hasattr(extractor, 'keyword_searcher') and extractor.keyword_searcher:
                        start_row, end_row = extractor.keyword_searcher.find_header_rows(table_data)
                        merged_header = extractor.keyword_searcher.build_merged_header(table_data, start_row, end_row)
                    else:
                        merged_header = [str(cell).strip() for cell in table_data[0]]

                    # 创建DataFrame（导出完整表格，包含表头行）
                    df = pd.DataFrame(table_data, columns=merged_header)
                    df["_来源文件"] = file_name
                    df["_来源页码"] = page_label
                    df["_来源表格"] = idx + 1

                    # 统计型号数量（数据行，跳过表头）
                    data_rows = len(table_data) - 1  # 减去表头
                    if is_summary:
                        # 表外型号汇总：型号数量 = 数据行数
                        model_count = data_rows
                    else:
                        # 普通表格：估算型号数量（数据行数）
                        model_count = data_rows
                    
                    model_stats_data.append({
                        "序号": idx + 1,
                        "文件名": file_name,
                        "页码": page_label,
                        "表格类型": "表外型号汇总" if is_summary else "普通表格",
                        "列数": len(merged_header),
                        "数据行数": data_rows,
                        "型号数量(估)": model_count,
                    })

                    # 设置sheet名称（限制31个字符），包含文件名
                    if table_info.get("is_model_summary"):
                        sheet_name = "表外型号汇总"
                    else:
                        base_name = os.path.splitext(file_name)[0][:15] if file_name else ""
                        sheet_name = f"表格{idx+1}_{base_name}_第{page_label}页".strip("_")
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:31]

                    # 写入sheet
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # 更新进度
                    progress = ((idx + 1) / total_tables) * 100
                    self.search_queue.put(("export_progress", progress))
                    self.search_queue.put(("export_count", idx + 1))

                # 写入型号统计汇总sheet
                if model_stats_data:
                    stats_df = pd.DataFrame(model_stats_data)
                    stats_df.to_excel(writer, sheet_name="型号统计汇总", index=False)
                    
                    # 创建按文件名分组的统计
                    try:
                        file_summary = stats_df.groupby("文件名").agg({
                            "数据行数": "sum",
                            "型号数量(估)": "sum"
                        }).reset_index()
                        file_summary.columns = ["文件名", "总数据行数", "总型号数量(估)"]
                        file_summary.to_excel(writer, sheet_name="按文件汇总", index=False)
                    except Exception:
                        pass

            self.search_queue.put(("export_done", file_path))

        except Exception as e:
            self.search_queue.put(("export_error", str(e)))
    
    def _update_export_progress(self):
        """
        更新导出进度
        
        从消息队列中读取进度信息并更新界面显示。
        """
        if not self.is_exporting and self.search_queue.empty():
            return

        try:
            while not self.search_queue.empty():
                msg_type, msg_data = self.search_queue.get_nowait()

                if msg_type == "export_progress":
                    self.progress_var.set(msg_data)
                    self.status_label.config(text=f"正在导出... {int(msg_data)}%")
                elif msg_type == "export_count":
                    self.status_label.config(text=f"已导出 {msg_data} 个表格")
                elif msg_type == "export_done":
                    self.is_exporting = False
                    self.progress_var.set(100)
                    self.status_label.config(text="导出完成")
                    
                    messagebox.showinfo("成功", f"所有表格已导出到:\n{msg_data}\n\n共导出 {len(self.tables)} 个表格")
                    if messagebox.askyesno("提示", "是否打开导出的 Excel 文件？"):
                        os.startfile(msg_data)
                    return
                elif msg_type == "export_error":
                    self.is_exporting = False
                    self.status_label.config(text="导出失败")
                    messagebox.showerror("错误", f"导出失败: {msg_data}")
                    return

        except queue.Empty:
            pass

        # 继续监听消息队列
        self.root.after(100, self._update_export_progress)

    def _export_excel(self):
        """
        导出Excel文件

        将当前搜索结果导出为Excel文件（.xlsx格式），使用openpyxl引擎。
        导出成功后询问用户是否打开文件。
        """
        if self.current_df is None or self.current_df.empty:
            messagebox.showwarning("警告", "没有数据可导出")
            return

        file_path = filedialog.asksaveasfilename(
            title="保存 Excel 文件",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")]
        )

        if file_path:
            try:
                # 处理去重
                export_df = self.current_df.copy()
                if self.remove_duplicates_var.get():
                    original_count = len(export_df)
                    export_df = export_df.drop_duplicates()
                    removed_count = original_count - len(export_df)
                    if removed_count > 0:
                        messagebox.showinfo("去重完成", f"已删除 {removed_count} 条重复数据")
                
                # 导出DataFrame到Excel
                export_df.to_excel(file_path, index=False, engine="openpyxl")
                messagebox.showinfo("成功", f"Excel 文件已保存到:\n{file_path}")
                if messagebox.askyesno("提示", "是否打开导出的 Excel 文件？"):
                    os.startfile(file_path)
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")


def main_gui():
    """
    主函数，启动GUI界面
    """
    root = tk.Tk()
    app = PDFTableExtractorGUI(root)
    try:
        root.mainloop()
    except Exception as e:
        import traceback
        error_log = f"错误日志 - {pd.Timestamp.now()}\n错误类型: {type(e).__name__}\n错误信息: {str(e)}\n完整堆栈:\n{traceback.format_exc()}"
        try:
            with open("error.log", "w", encoding="utf-8") as f:
                f.write(error_log)
            messagebox.showerror("严重错误", f"程序发生严重错误，详细信息已保存到 error.log\n\n错误类型: {type(e).__name__}\n错误信息: {str(e)}")
        except:
            messagebox.showerror("严重错误", f"程序发生严重错误\n\n错误类型: {type(e).__name__}\n错误信息: {str(e)}")


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main_gui()