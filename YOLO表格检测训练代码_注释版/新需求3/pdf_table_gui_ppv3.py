"""
PDF表格数据提取器 - PP-StructureV3版本 GUI界面
"""

import os
import sys
import threading
import queue
import tkinter as tk
import logging
from datetime import datetime
from tkinter import ttk, filedialog, messagebox
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_table_extractor_ppv3 import PDFTableExtractorPPV3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app_ppv3.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PDFTableExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF表格提取器 - PP-StructureV3版本")
        self.root.geometry("900x600")
        
        self.extractor = None
        self.current_file = ""
        self.current_tables = {}
        self.search_queue = queue.Queue()
        self.search_thread = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="5")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_frame, text="浏览PDF文件", command=self._select_files).pack(side=tk.LEFT, padx=5)
        self.file_label = ttk.Label(file_frame, text="未选择文件")
        self.file_label.pack(side=tk.LEFT, padx=5)
        
        action_frame = ttk.LabelFrame(main_frame, text="操作", padding="5")
        action_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(action_frame, text="识别表格", command=self._extract_tables).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="导出Excel", command=self._export_excel).pack(side=tk.LEFT, padx=5)
        
        progress_frame = ttk.LabelFrame(main_frame, text="进度", padding="5")
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.StringVar(value="等待操作...")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
        
        result_frame = ttk.LabelFrame(main_frame, text="识别结果", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ("页码", "表格数", "详情")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        self.result_tree.heading("页码", text="页码")
        self.result_tree.heading("表格数", text="表格数")
        self.result_tree.heading("详情", text="详情")
        self.result_tree.column("页码", width=80)
        self.result_tree.column("表格数", width=80)
        self.result_tree.column("详情", width=300)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _select_files(self):
        file_path = filedialog.askopenfilename(
            title="选择PDF文件",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if file_path:
            self.current_file = file_path
            self.file_label.config(text=os.path.basename(file_path))
    
    def _extract_tables(self):
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择PDF文件")
            return
        
        self.progress_var.set("正在初始化PP-StructureV3...")
        self.progress_bar.start()
        
        def extract_worker():
            try:
                self.extractor = PDFTableExtractorPPV3(self.current_file)
                self.current_tables = self.extractor.extract_all_pages()
                
                self.search_queue.put(('done', self.current_tables))
            except Exception as e:
                logger.error(f"提取失败: {e}")
                self.search_queue.put(('error', str(e)))
        
        self.search_thread = threading.Thread(target=extract_worker)
        self.search_thread.start()
        
        self.root.after(100, self._check_search_queue)
    
    def _check_search_queue(self):
        try:
            msg = self.search_queue.get_nowait()
            if msg[0] == 'done':
                self.progress_bar.stop()
                self._display_results(msg[1])
            elif msg[0] == 'error':
                self.progress_bar.stop()
                self.progress_var.set(f"错误: {msg[1]}")
                messagebox.showerror("错误", f"提取失败: {msg[1]}")
        except queue.Empty:
            if self.search_thread.is_alive():
                self.root.after(100, self._check_search_queue)
                return
    
    def _display_results(self, tables):
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        total_tables = 0
        for page_num, page_tables in tables.items():
            total_tables += len(page_tables)
            details = []
            for i, table in enumerate(page_tables):
                rows = len(table)
                cols = len(table[0]) if table else 0
                details.append(f"表格{i+1}: {rows}行x{cols}列")
            
            self.result_tree.insert("", tk.END, values=(
                page_num + 1,
                len(page_tables),
                "; ".join(details)
            ))
        
        self.progress_var.set(f"识别完成，共识别到 {total_tables} 个表格")
    
    def _export_excel(self):
        if not self.current_tables:
            messagebox.showwarning("警告", "请先识别表格")
            return
        
        output_path = filedialog.asksaveasfilename(
            title="保存Excel文件",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        
        if not output_path:
            return
        
        if self.extractor:
            success = self.extractor.export_to_excel(output_path)
            if success:
                self.progress_var.set(f"导出成功: {output_path}")
                messagebox.showinfo("成功", f"Excel文件已保存到:\n{output_path}")
            else:
                messagebox.showerror("错误", "导出失败")


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFTableExtractorGUI(root)
    root.mainloop()
