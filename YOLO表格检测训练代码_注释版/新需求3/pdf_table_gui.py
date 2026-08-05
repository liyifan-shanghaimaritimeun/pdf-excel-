"""
PDF表格数据提取器 - GUI界面

使用Tkinter构建的图形界面，提供以下功能：
1. PDF文件选择和浏览
2. 页码范围输入（支持全选、单页、范围）
3. 关键词输入和快捷按钮
4. 表格识别和预览
5. 关键词搜索（单表搜索、全部表格搜索）
6. 搜索进度显示
7. 数据预览和导出Excel

界面布局：
- 顶部工具栏：文件选择、页码输入、识别表格按钮
- 关键词区域：输入框、快捷按钮
- 表格选择区域：下拉框、预览按钮、搜索按钮
- 进度条区域：进度显示、状态提示
- 操作按钮区域：导出Excel按钮
- 数据预览区域：表格展示、统计信息
"""

import os
import sys
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_table_extractor import PDFTableExtractor


class PDFTableExtractorGUI:
    """
    PDF表格提取器GUI主类

    负责界面初始化、事件处理、搜索逻辑和数据展示。
    """

    def __init__(self, root):
        """
        初始化GUI界面

        Args:
            root: Tkinter根窗口
        """
        self.root = root
        self.root.title("PDF 表格数据提取器")
        self.root.geometry("1200x800")

        # 数据状态
        self.current_df = None           # 当前搜索结果DataFrame
        self.pdf_path = ""               # PDF文件路径
        self.tables = []                 # 识别到的表格列表
        self.current_table_index = 0     # 当前选中的表格索引
        self.extractor = None            # PDF表格提取器实例
        self.pdf_page_count = 0          # PDF总页数
        self.is_searching = False        # 是否正在搜索
        self.search_queue = queue.Queue()  # 搜索进度消息队列

        # 创建界面控件
        self._create_widgets()

    def _create_widgets(self):
        """创建所有界面控件"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 工具栏区域 ==========
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, pady=5)

        # PDF文件选择
        ttk.Label(toolbar_frame, text="PDF 文件:").pack(side=tk.LEFT, padx=5)
        self.pdf_path_var = tk.StringVar()
        pdf_entry = ttk.Entry(toolbar_frame, textvariable=self.pdf_path_var, width=50)
        pdf_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar_frame, text="浏览", command=self._browse_pdf).pack(side=tk.LEFT, padx=5)

        # 页码输入
        page_frame = ttk.Frame(toolbar_frame)
        page_frame.pack(side=tk.LEFT, padx=10)
        
        ttk.Label(page_frame, text="页码:").pack(side=tk.LEFT, padx=5)
        self.page_range_var = tk.StringVar(value="全选")
        page_entry = ttk.Entry(page_frame, textvariable=self.page_range_var, width=10)
        page_entry.pack(side=tk.LEFT, padx=5)

        # 识别表格按钮
        ttk.Button(toolbar_frame, text="识别表格", command=self._extract_tables).pack(side=tk.RIGHT, padx=5)

        # ========== 关键词搜索区域 ==========
        keyword_frame = ttk.LabelFrame(main_frame, text="搜索关键词（逗号分隔）", padding="10")
        keyword_frame.pack(fill=tk.X, pady=5)

        ttk.Label(keyword_frame, text="输入要搜索的表头关键词，如 partnumber, cap, wv:").pack(anchor=tk.W)
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
        ttk.Button(table_frame, text="搜索数据", command=self._search_data).pack(side=tk.RIGHT, padx=5)
        ttk.Button(table_frame, text="搜索全部表格", command=self._search_all_pages).pack(side=tk.RIGHT, padx=5)

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

        ttk.Button(action_frame, text="导出 Excel", command=self._export_excel).pack(side=tk.RIGHT, padx=5)

        # ========== 数据预览区域 ==========
        preview_frame = ttk.LabelFrame(main_frame, text="数据预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 表格控件
        self.tree = ttk.Treeview(preview_frame, show="headings")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 垂直滚动条
        scrollbar_y = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        # 水平滚动条
        scrollbar_x = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(xscrollcommand=scrollbar_x.set)

        # 统计信息标签
        self.stats_label = ttk.Label(preview_frame, text="")
        self.stats_label.pack(side=tk.BOTTOM, pady=5)

    def _browse_pdf(self):
        """
        浏览并选择PDF文件

        弹出文件选择对话框，选择PDF文件后初始化提取器并获取文件信息。
        """
        file_path = filedialog.askopenfilename(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_path:
            self.pdf_path_var.set(file_path)
            self.pdf_path = file_path
            self.extractor = PDFTableExtractor(file_path, use_ocr=True)

            # 获取PDF文件信息（页数和大小）
            try:
                import fitz
                doc = fitz.open(file_path)
                self.pdf_page_count = doc.page_count
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                messagebox.showinfo("提示", f"PDF 文件共 {self.pdf_page_count} 页，大小: {file_size:.1f} MB")
            except Exception as e:
                pass

    def _add_keyword(self, keyword):
        """
        添加关键词到输入框

        Args:
            keyword: 要添加的关键词
        """
        current_text = self.keywords_text.get("1.0", tk.END).strip()
        if current_text:
            # 避免重复添加
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

    def _parse_page_range(self):
        """
        解析页码范围输入

        支持三种格式：
        - "全选" 或 "all": 返回所有页码
        - 单个数字（如 "2"）: 返回该页码
        - 范围（如 "1-5"）: 返回起始到结束的所有页码

        Returns:
            页码列表（从0开始）
        """
        page_range = self.page_range_var.get().strip()
        
        if page_range.lower() == "全选" or page_range.lower() == "all":
            if self.pdf_page_count > 0:
                return list(range(self.pdf_page_count))
            return [0]
        
        if page_range.isdigit():
            return [int(page_range)]
        
        if "-" in page_range:
            parts = page_range.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start = int(parts[0])
                end = int(parts[1])
                return list(range(start, end + 1))
        
        return [0]

    def _extract_tables(self):
        """
        提取PDF中的表格

        根据页码范围，在指定页面中识别表格并显示在下拉框中。
        提取完成后自动预览第一个表格。
        """
        pdf_path = self.pdf_path_var.get().strip()
        if not pdf_path:
            messagebox.showwarning("警告", "请选择 PDF 文件")
            return

        if not os.path.exists(pdf_path):
            messagebox.showerror("错误", "PDF 文件不存在")
            return

        # 获取PDF页数（必须在_parse_page_range之前调用）
        try:
            import fitz
            doc = fitz.open(pdf_path)
            self.pdf_page_count = doc.page_count
        except:
            self.pdf_page_count = 0

        page_nums = self._parse_page_range()

        # 确保提取器已初始化
        if not hasattr(self, 'extractor') or not self.extractor:
            self.extractor = PDFTableExtractor(pdf_path, use_ocr=True)

        # 设置等待光标
        self.root.config(cursor="wait")
        self.root.update()

        try:
            self.tables = []
            
            # 遍历指定页面提取表格
            for page_num in page_nums:
                if self.pdf_page_count > 0 and page_num >= self.pdf_page_count:
                    continue
                page_tables = self.extractor.extract_tables(page_num)
                for table in page_tables:
                    table_info = {
                        "data": table,
                        "page_num": page_num,
                        "file_path": pdf_path
                    }
                    self.tables.append(table_info)

            # 处理未识别到表格的情况
            if not self.tables:
                messagebox.showinfo("提示", "未识别到表格")
                self.table_combobox["values"] = []
                return

            # 更新表格下拉框
            table_options = []
            for i, table_info in enumerate(self.tables):
                table = table_info["data"]
                cols = len(table[0]) if table else 0
                rows = len(table)
                page_num = table_info["page_num"]
                table_options.append(f"表格 {i+1} (第{page_num+1}页, {rows}行 x {cols}列)")

            self.table_combobox["values"] = table_options
            self.table_var.set(table_options[0])
            self.current_table_index = 0

            messagebox.showinfo("成功", f"在 {len(page_nums)} 页中识别到 {len(self.tables)} 个表格")

            # 预览第一个表格
            self._preview_raw_table()

        except Exception as e:
            import traceback
            detailed_error = f"提取失败: {str(e)}\n\n详细错误:\n{traceback.format_exc()}"
            try:
                with open("extract_error.log", "w", encoding="utf-8") as f:
                    f.write(detailed_error)
            except:
                pass
            messagebox.showerror("错误", f"提取失败: {str(e)}\n\n详细信息已保存到 extract_error.log")
        finally:
            # 恢复正常光标
            self.root.config(cursor="")

    def _on_table_selected(self, event):
        """
        表格选择事件处理

        当用户从下拉框选择表格时，更新当前表格索引并预览该表格。

        Args:
            event: 事件对象
        """
        selected = self.table_var.get()
        if selected:
            self.current_table_index = int(selected.split()[1]) - 1
            self._preview_raw_table()

    def _preview_raw_table(self):
        """
        预览原始表格

        在数据预览区域显示当前选中表格的完整内容，表头行高亮显示。
        """
        if not self.tables or self.current_table_index >= len(self.tables):
            return

        table_info = self.tables[self.current_table_index]
        table = table_info["data"]
        page_num = table_info["page_num"]

        # 清空现有表格
        for item in self.tree.get_children():
            self.tree.delete(item)

        # 清空列定义
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        self.tree["columns"] = ()

        if not table:
            self.stats_label.config(text="空表格")
            return

        # 识别表头行并合并
        start_row, end_row = self.extractor.keyword_searcher.find_header_rows(table)
        columns = [str(i) for i in range(len(table[0]))]
        self.tree["columns"] = columns

        merged_header = self.extractor.keyword_searcher.build_merged_header(table, start_row, end_row)

        # 设置列标题和宽度
        for i in range(len(table[0])):
            header_text = merged_header[i][:30] + "..." if len(merged_header[i]) > 30 else merged_header[i]
            self.tree.heading(str(i), text=f"列{i+1}: {header_text}")
            self.tree.column(str(i), width=120, minwidth=80)

        # 插入表格数据
        for idx, row in enumerate(table):
            values = []
            for cell in row:
                cell_str = str(cell)[:50] + "..." if len(str(cell)) > 50 else str(cell)
                values.append(cell_str)

            # 表头行添加高亮标签
            tag = "header" if start_row <= idx <= end_row else ""
            self.tree.insert("", tk.END, values=values, tags=(tag,))

        # 设置表头行样式
        self.tree.tag_configure("header", background="#e0e0e0")

        # 更新统计信息
        self.stats_label.config(text=f"原始表格: 第{page_num+1}页, {len(table)} 行, {len(table[0])} 列, 表头行: {start_row}-{end_row}")

    def _search_data(self):
        """
        搜索数据（在当前选中表格中搜索）

        解析关键词后，启动后台线程进行搜索，并更新进度条。
        """
        keywords = self._parse_keywords()
        if not keywords:
            return

        self.is_searching = True
        self.progress_var.set(0)
        self.status_label.config(text="正在搜索...")
        
        # 清空现有数据
        self.current_df = None
        self._clear_tree()
        self.stats_label.config(text="")

        # 启动后台搜索线程
        thread = threading.Thread(target=self._search_worker, args=(keywords,), daemon=True)
        thread.start()
        
        # 启动进度更新循环
        self._update_progress()

    def _search_worker(self, keywords):
        """
        搜索工作线程

        使用多线程并行处理多个页面，搜索包含关键词的数据。
        搜索结果通过队列传递给主线程更新UI。

        Args:
            keywords: 关键词列表
        """
        if not self.extractor:
            self.extractor = PDFTableExtractor(self.pdf_path, use_ocr=True)

        # 获取PDF总页数
        try:
            import fitz
            doc = fitz.open(self.pdf_path)
            total_pages = doc.page_count
            doc.close()
        except Exception:
            total_pages = 100

        all_data = []
        processed_pages = 0
        
        # 使用单线程顺序处理，避免多线程环境下Cython模块的兼容性问题
        for page_num in range(total_pages):
            if not self.is_searching:
                break
            
            try:
                results = self.extractor.search_by_keyword(page_num, keywords)
                for table_result in results["results"]:
                    for row in table_result["data"]:
                        row_copy = row.copy()
                        row_copy["_页码"] = page_num + 1
                        row_copy["_来源表格"] = f"表格{table_result['table_index']+1}"
                        row_copy["_来源行号"] = row_copy.get("_source_row", "")
                        all_data.append(row_copy)
            except Exception as e:
                print(f"处理第{page_num+1}页时出错: {e}")
            
            # 更新进度
            processed_pages += 1
            progress = (processed_pages / total_pages) * 100
            self.search_queue.put(("progress", progress))
            self.search_queue.put(("count", len(all_data)))

        # 搜索完成，传递结果
        self.search_queue.put(("done", all_data, keywords))

    def _update_progress(self):
        """
        更新搜索进度

        从队列中获取进度消息，更新进度条和状态标签。
        使用after方法实现非阻塞更新。
        """
        if not self.is_searching and self.search_queue.empty():
            return

        try:
            while not self.search_queue.empty():
                msg_type, *args = self.search_queue.get_nowait()
                
                if msg_type == "progress":
                    self.progress_var.set(args[0])
                    self.status_label.config(text=f"正在处理: {int(args[0])}%")
                elif msg_type == "count":
                    self.stats_label.config(text=f"已找到 {args[0]} 条数据")
                elif msg_type == "done":
                    all_data, keywords = args[0], args[1]
                    self._finish_search(all_data, keywords)
                    return
        except queue.Empty:
            pass

        # 继续更新进度
        self.root.after(200, self._update_progress)

    def _finish_search(self, all_data, keywords):
        """
        完成搜索处理

        将搜索结果转换为DataFrame，并更新预览区域。

        Args:
            all_data: 搜索到的数据列表
            keywords: 关键词列表
        """
        self.is_searching = False
        self.progress_var.set(100)
        self.status_label.config(text="搜索完成")

        if not all_data:
            messagebox.showinfo("提示", f"未找到包含关键词 '{', '.join(keywords)}' 的数据")
            return

        # 转换为DataFrame
        self.current_df = pd.DataFrame(all_data)

        # 按关键词顺序排列列，最后显示来源信息（包含表头标识）
        cols_order = [k for k in keywords if k in self.current_df.columns]
        cols_order.extend(["_页码", "_来源行号", "_来源表格"])
        # 添加表头标识列（如果存在）
        if "_is_header" in self.current_df.columns:
            cols_order.insert(-1, "_is_header")
        self.current_df = self.current_df[cols_order]

        messagebox.showinfo("成功", f"找到 {len(self.current_df)} 条匹配数据")
        self._refresh_preview()

    def _search_all_pages(self):
        """
        搜索全部页面

        在PDF所有页面的所有表格中搜索包含关键词的数据。
        """
        keywords = self._parse_keywords()
        if not keywords:
            return

        self.is_searching = True
        self.progress_var.set(0)
        self.status_label.config(text="正在搜索全部页面...")
        
        self.current_df = None
        self._clear_tree()
        self.stats_label.config(text="")

        thread = threading.Thread(target=self._search_worker, args=(keywords,), daemon=True)
        thread.start()
        
        self._update_progress()

    def _clear_tree(self):
        """
        清空预览表格

        删除所有行和列定义。
        """
        for item in self.tree.get_children():
            self.tree.delete(item)
        for col in self.tree["columns"]:
            self.tree.heading(col, text="")
        self.tree["columns"] = ()

    def _refresh_preview(self):
        """
        刷新数据预览

        根据当前DataFrame更新预览表格。
        """
        self._clear_tree()

        if self.current_df is None or self.current_df.empty:
            self.stats_label.config(text="暂无数据")
            return

        columns = list(self.current_df.columns)
        self.tree["columns"] = columns

        # 设置列标题和宽度
        for col in columns:
            self.tree.heading(col, text=str(col))
            self.tree.column(col, width=120, minwidth=80)

        # 最多显示1000行
        display_rows = min(len(self.current_df), 1000)
        for idx in range(display_rows):
            row = self.current_df.iloc[idx]
            values = []
            for col in columns:
                val = row[col]
                if pd.isna(val):
                    values.append("")
                else:
                    val_str = str(val)
                    if len(val_str) > 50:
                        val_str = val_str[:50] + "..."
                    values.append(val_str)
            self.tree.insert("", tk.END, values=values)

        # 更新统计信息
        if len(self.current_df) > 1000:
            self.stats_label.config(text=f"共 {len(self.current_df)} 行, 显示前 1000 行")
        else:
            self.stats_label.config(text=f"共 {len(self.current_df)} 行")

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

        # 如果表格为空，提示用户
        if not table_data or len(table_data) < 2:
            messagebox.showwarning("警告", "选中的表格数据为空")
            return

        # 识别表头行并合并
        start_row, end_row = 0, 0
        if self.extractor:
            start_row, end_row = self.extractor.keyword_searcher.find_header_rows(table_data)
            merged_header = self.extractor.keyword_searcher.build_merged_header(table_data, start_row, end_row)
        else:
            # 如果没有提取器实例，使用第一行作为表头
            merged_header = [str(cell).strip() for cell in table_data[0]]

        # 创建DataFrame（导出完整表格，包含表头行）
        # 使用所有行数据，包括表头行
        df = pd.DataFrame(table_data, columns=merged_header)

        # 添加来源信息列
        df["_来源页码"] = page_num + 1
        df["_来源表格"] = self.current_table_index + 1

        # 弹出保存对话框
        file_path = filedialog.asksaveasfilename(
            title="保存选中表格 - Excel 文件",
            defaultextension=".xlsx",
            filetypes=[("Excel 文件", "*.xlsx"), ("所有文件", "*.*")],
            initialfile=f"表格{self.current_table_index + 1}_第{page_num + 1}页.xlsx"
        )

        if file_path:
            try:
                # 导出DataFrame到Excel
                df.to_excel(file_path, index=False, engine="openpyxl")
                messagebox.showinfo("成功", f"Excel 文件已保存到:\n{file_path}")
                # 询问是否打开文件
                if messagebox.askyesno("提示", "是否打开导出的 Excel 文件？"):
                    os.startfile(file_path)
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")

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
                # 导出DataFrame到Excel
                self.current_df.to_excel(file_path, index=False, engine="openpyxl")
                messagebox.showinfo("成功", f"Excel 文件已保存到:\n{file_path}")
                # 询问是否打开文件
                if messagebox.askyesno("提示", "是否打开导出的 Excel 文件？"):
                    os.startfile(file_path)
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")


def main_gui():
    """
    GUI入口函数

    创建根窗口并启动应用。
    """
    root = tk.Tk()
    app = PDFTableExtractorGUI(root)
    try:
        root.mainloop()
    except Exception as e:
        import traceback
        error_log = f"""错误日志 - {time.strftime('%Y-%m-%d %H:%M:%S')}
错误类型: {type(e).__name__}
错误信息: {str(e)}
完整堆栈:
{traceback.format_exc()}
"""
        try:
            with open("error.log", "w", encoding="utf-8") as f:
                f.write(error_log)
            messagebox.showerror("严重错误", f"程序发生严重错误，详细信息已保存到 error.log\n\n错误类型: {type(e).__name__}\n错误信息: {str(e)}")
        except:
            messagebox.showerror("严重错误", f"程序发生严重错误\n\n错误类型: {type(e).__name__}\n错误信息: {str(e)}")


if __name__ == "__main__":
    main_gui()