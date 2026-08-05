"""
PDF表格数据提取器

核心功能：
1. 使用PyMuPDF(fitz)进行PDF版面分析和文本提取
2. 集成PaddleOCR处理复杂表格或扫描件
3. 支持先字典后泛化的表头搜索策略
4. 自动识别双栏表格并分割处理
5. 使用Pandas进行数据清洗和导出

适用场景：
- PDF产品目录表格提取
- 扫描件表格识别
- 多页PDF批量提取
- 大文件(200MB+)处理
"""

import os
import re
import threading
import fitz
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any


class OCRTableExtractor:
    """
    OCR表格识别器

    使用PaddleOCR对PDF页面进行文字识别，将识别结果转换为带坐标信息的单元格列表。
    支持中英文混合识别，自动处理文字方向。
    """

    _ocr_lock = threading.Lock()

    def __init__(self, use_gpu: bool = False):
        """
        初始化OCR识别器

        Args:
            use_gpu: 是否使用GPU加速，默认False
        """
        self.use_gpu = use_gpu
        self.ocr = None
        self._init_ocr()

    def _init_ocr(self):
        """初始化PaddleOCR实例（延迟加载）"""
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                lang='ch',           # 中英文混合识别
                use_gpu=self.use_gpu,
                use_angle_cls=True,  # 启用文字方向分类
                show_log=False       # 关闭日志输出
            )
        except ImportError:
            pass
        except Exception as e:
            print(f"OCR初始化失败: {e}")
            self.ocr = None

            

    def recognize_from_image(self, image_path: str) -> List[Dict]:
        """
        从图片中识别文字，返回带坐标信息的单元格列表

        Args:
            image_path: 图片文件路径

        Returns:
            单元格列表，每个单元格包含：text(文字), x0/y0/x1/y1(边界坐标), center_x/center_y(中心坐标)
        """
        if not self.ocr:
            return []

        try:
            # 添加线程锁，确保OCR识别线程安全
            with self._ocr_lock:
                result = self.ocr.ocr(image_path, cls=True)
                if not result or not result[0]:
                    print(f"✗ OCR识别失败: {image_path}")
                    return []


                  
                cells = []
                for line in result[0]:
                    box = line[0]       # 边界框坐标
                    text = line[1][0]   # 识别文字

                    x0, y0 = box[0]     # 左上角坐标
                    x1, y1 = box[2]     # 右下角坐标

                    cells.append({
                        "text": text.strip(),
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "center_x": (x0 + x1) / 2,  # X中心坐标
                        "center_y": (y0 + y1) / 2,  # Y中心坐标
                    })

                return cells
        except Exception:
            return []

    def recognize_from_pdf_page(self, pdf_path: str, page_num: int = 0) -> List[Dict]:
        """
        从PDF指定页面识别文字

        Args:
            pdf_path: PDF文件路径
            page_num: 页码（从0开始）

        Returns:
            单元格列表，每个单元格包含文字和坐标信息
        """
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)

        # 将PDF页面渲染为图片，放大1.5倍提高识别精度
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))

        # 保存临时图片文件
        temp_path = f"_temp_page_{page_num}.png"
        pix.save(temp_path)

        # 调用OCR识别
        cells = self.recognize_from_image(temp_path)

        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return cells

    def recognize_table_with_ppstructure(self, image_path: str) -> List[List[List[str]]]:
        """
        使用PPStructure专用接口识别表格结构

        Args:
            image_path: 图片文件路径

        Returns:
            表格数据列表，每个表格是一个二维列表
        """
        try:
            from paddleocr import PaddleOCR
            table_engine = PaddleOCR(
                lang='ch',
                use_gpu=self.use_gpu,
                use_angle_cls=True,
                show_log=False,
                table=True
            )
            
            with self._ocr_lock:
                result = table_engine.ocr(image_path, cls=True)
            
            if not result or not result[0]:
                return []
            
            tables = []
            for item in result[0]:
                if isinstance(item, dict) and 'table' in item:
                    table_data = item['table']
                    if table_data and isinstance(table_data, list):
                        tables.append(table_data)
            
            return tables
        except Exception:
            return []


class TableStructureAnalyzer:
    """
    表格结构分析器

    负责表格数据的清洗、双栏表格分割等结构处理。
    """

    def __init__(self):
        """初始化表格结构分析器"""
        pass

    def clean_table(self, table: List[List[str]]) -> List[List[str]]:
        """
        清洗表格数据：去除空白行，清理单元格内容

        Args:
            table: 原始表格数据（二维列表）

        Returns:
            清洗后的表格数据，不包含全空行
        """
        cleaned = []
        for row in table:
            # 将每个单元格转换为字符串并去除首尾空格
            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
            # 只保留非空行
            if any(cleaned_row):
                cleaned.append(cleaned_row)
        return cleaned

    def split_double_table(self, table: List[List[str]]) -> List[List[List[str]]]:
        """
        自动检测并分割双栏表格

        双栏表格是指PDF中常见的并排显示的两个表格，左右两部分通常是对称的。
        该方法采用两种策略进行分割：
        1. 对称分割（优先）：双栏表格左右列数大致相等，按中间位置分割
        2. 空白列分割（备选）：通过检测中间空白列确定分割位置

        改进点：
        1. 优先使用对称分割，符合PDF表格的实际布局特点
        2. 通过表头结构验证分割结果的正确性
        3. 分割后对每个子表格独立清洗，避免数据丢失

        Args:
            table: 原始表格数据

        Returns:
            分割后的表格列表，可能是1个或2个表格
        """
        if not table or len(table) == 0:
            return [table]

        num_cols = len(table[0])
        # 列数少于6列的通常不是双栏表格，直接清洗返回
        if num_cols < 6:
            cleaned = self.clean_table(table)
            return [cleaned] if len(cleaned) >= 2 else [table]

        # 策略1：优先使用对称分割
        # 双栏表格左右列数通常大致相等，尝试在中间位置分割
            split_col = self._find_symmetric_split(table)

        # 策略2：如果对称分割不可行，尝试空白列分割
        if split_col <= 0:
            split_col = self._find_separator_by_empty_col(table)

        # 如果找到了有效的分割列
        if split_col > 0 and split_col < num_cols - 2:
            table1 = []
            table2 = []
            for row in table:
                row1 = row[:split_col]
                row2 = row[split_col:]
                table1.append(row1)
                table2.append(row2)

            # 对每个子表格进行独立清洗
            cleaned_table1 = self.clean_table(table1)
            cleaned_table2 = self.clean_table(table2)

            # 验证分割结果：两个子表格都应有足够的数据
            result = []
            if len(cleaned_table1) >= 2:
                result.append(cleaned_table1)
            if len(cleaned_table2) >= 2:
                result.append(cleaned_table2)

            return result if result else [table]

        # 不是双栏表格，直接清洗返回
        cleaned = self.clean_table(table)
        return [cleaned] if len(cleaned) >= 2 else [table]

    def _find_symmetric_split(self, table: List[List[str]]) -> int:
        """
        通过对称分析找到分割列位置

        双栏表格的特点：
        1. 左右两部分有相同或相似的表头结构
        2. 列数大致相等
        3. 表头列名会重复出现（如左边有"Part Number"，右边也会有）

        改进点：
        1. 使用多行表头进行对称分析，而非仅单行
        2. 排除产品型号行（如HSE102M51），避免误判分割点
        3. 通过多行列结构对比确定更准确的分割位置

        Args:
            table: 表格数据

        Returns:
            分割列索引，未找到返回0
        """
        if not table or len(table) < 2:
            return 0

        num_cols = len(table[0])
        # 至少需要6列才可能是双栏表格
        if num_cols < 6:
            return 0

        # 使用多行表头进行分析（前5行）
        header_rows = table[:min(5, len(table))]
        
        # 收集所有表头行的关键词（排除产品型号行）
        all_header_keywords = set()
        for row in header_rows:
            for cell in row:
                cell_str = str(cell).strip().lower()
                if cell_str and len(cell_str) >= 2:
                    # 排除产品型号模式（如HSE102M51）
                    if not re.match(r'^[a-zA-Z0-9]+$', str(cell).strip()):
                        all_header_keywords.add(cell_str)

        if len(all_header_keywords) < 2:
            return 0

        # 方法1：通过找到重复的表头关键词确定分割位置
        # 从左到右扫描，找到第一个重复出现的表头关键词位置
        split_col = 0
        found_first_keyword = False
        first_keyword = ""
        
        # 遍历所有表头行，寻找重复的关键词模式
        for row in header_rows:
            for col_idx, cell in enumerate(row):
                cell_str = str(cell).strip().lower()
                if cell_str in all_header_keywords:
                    # 排除纯数字产品型号
                    if re.match(r'^[a-zA-Z0-9]+$', str(cell).strip()):
                        continue
                        
                    if not found_first_keyword:
                        found_first_keyword = True
                        first_keyword = cell_str
                    else:
                        # 如果找到相同的关键词，说明这是右栏的开始
                        if cell_str == first_keyword and col_idx > num_cols // 3:
                            split_col = col_idx
                            return split_col

        # 方法2：基于列数对称性的分割
        # 双栏表格左右列数通常相等，尝试在中间位置分割
        left_half_cols = num_cols // 2
        
        # 验证左右两部分是否有相似的结构
        left_keywords = set()
        right_keywords = set()
        
        for row in header_rows:
            # 左半部分关键词
            for col_idx in range(left_half_cols):
                if col_idx < len(row):
                    cell_str = str(row[col_idx]).strip().lower()
                    if cell_str and len(cell_str) >= 2:
                        if not re.match(r'^[a-zA-Z0-9]+$', str(row[col_idx]).strip()):
                            left_keywords.add(cell_str)
            
            # 右半部分关键词
            for col_idx in range(left_half_cols, num_cols):
                if col_idx < len(row):
                    cell_str = str(row[col_idx]).strip().lower()
                    if cell_str and len(cell_str) >= 2:
                        if not re.match(r'^[a-zA-Z0-9]+$', str(row[col_idx]).strip()):
                            right_keywords.add(cell_str)

        # 如果左右两部分有重叠的关键词，说明是双栏表格
        common_keywords = left_keywords & right_keywords
        
        if len(common_keywords) >= 1:
            # 找到第一个重复关键词在右半部分出现的位置
            for row in header_rows:
                for col_idx in range(left_half_cols, num_cols):
                    if col_idx < len(row):
                        cell_str = str(row[col_idx]).strip().lower()
                        if cell_str in common_keywords:
                            return col_idx
            
            # 如果没有找到具体位置，返回中间位置
            return left_half_cols

        # 方法3：检查是否有空白区域作为分隔（用于更准确的分割）
        # 统计每列的空白率
        check_rows = min(6, len(table))
        for col_idx in range(num_cols // 3, num_cols * 2 // 3):
            empty_count = 0
            for row_idx in range(check_rows):
                row = table[row_idx]
                if col_idx < len(row) and str(row[col_idx]).strip() == "":
                    empty_count += 1
            # 如果这一列空白率很高，且前后都有数据，说明是分隔列
            if empty_count >= check_rows * 0.5:
                # 检查前后是否有数据
                has_left_data = False
                has_right_data = False
                for row_idx in range(check_rows):
                    row = table[row_idx]
                    if col_idx > 0 and col_idx - 1 < len(row) and str(row[col_idx - 1]).strip():
                        has_left_data = True
                    if col_idx + 1 < len(row) and str(row[col_idx + 1]).strip():
                        has_right_data = True
                if has_left_data and has_right_data:
                    return col_idx

        return 0

    def _find_separator_by_empty_col(self, table: List[List[str]]) -> int:
        """
        通过空白列找到分割位置（备选策略）

        Args:
            table: 表格数据

        Returns:
            分割列索引，未找到返回0
        """
        if not table or len(table) < 2:
            return 0

        num_cols = len(table[0])
        if num_cols < 6:
            return 0

        # 找到表头行
        header_row = 0
        header_keywords = ['catalog', 'part', 'number', '型号', '编码', 'series']
        for i, row in enumerate(table[:min(6, len(table))]):
            if any(kw in str(cell).lower() for kw in header_keywords for cell in row):
                header_row = i
                break

        # 在中间区域寻找空白列作为分隔符
        check_rows = min(header_row + 10, len(table))
        separator_col = -1
        max_empty_ratio = 0.0

        # 只在中间1/3区域查找分隔列
        start_col = num_cols // 3
        end_col = num_cols * 2 // 3

        for col_idx in range(start_col, end_col):
            empty_count = 0
            for row_idx in range(check_rows):
                row = table[row_idx]
                if col_idx < len(row) and str(row[col_idx]).strip() == "":
                     empty_count += 1
            # 计算空白率
            empty_ratio = empty_count / check_rows
            if empty_ratio > max_empty_ratio:
                max_empty_ratio = empty_ratio
                separator_col = col_idx

        # 空白率 >= 60% 才认为是有效的分隔列
        if separator_col > 0 and max_empty_ratio >= 0.6:
            return separator_col

        return 0


class KeywordSearcher:
    """
    关键词搜索器

    负责表头识别、关键词匹配、先字典后泛化的搜索策略。
    """

    # 关键词规则字典：定义常用表头的同义词映射
    KEYWORD_RULES = {
        'partnumber': {
            'keywords': ['partnumber', 'part', 'number', '型号', '编码', 'code', 'pn', 'partno', '产品编码', '型号规格', 'catalog part number', 'catalog'],
            'column_hints': ['型号', '编码', 'part', 'code', 'pn', 'catalog']
        },
        'cap': {
            'keywords': ['cap', 'capacitance', '静电容量', '容量', 'c', '电容'],
            'column_hints': ['cap', 'capacitance', '电容', '容量', 'c']
        },
        'wv': {
            'keywords': ['wv', 'voltage', '额定电压', 'ur', '工作电压', 'voltage range', '电压', 'wvd', 'wvdc', 'surge'],
            'column_hints': ['wv', 'voltage', 'ur', '电压', 'v', 'wvd']
        },
        'size': {
            'keywords': ['size', '尺寸', 'dimension', '规格', '直径', '高度', 'diameter'],
            'column_hints': ['size', 'dimension', '尺寸', '规格', 'd', 'h']
        },
        'tolerance': {
            'keywords': ['tolerance', '公差', '容差'],
            'column_hints': ['tolerance', '公差', '容差']
        },
        'series': {
            'keywords': ['series', '系列'],
            'column_hints': ['series', '系列']
        }
    }

    def __init__(self):
        """初始化关键词搜索器"""
        pass

    def _contains_keyword(self, text: str, keywords: List[str]) -> bool:
        """
        判断文本是否包含任一关键词

        Args:
            text: 待检测文本
            keywords: 关键词列表

        Returns:
            True表示包含关键词，False表示不包含
        """
        text_lower = str(text).lower().strip()
        if not text_lower:
            return False
        for kw in keywords:
            # 完全匹配或包含匹配（文本长度不超过60字符）
            if kw.lower() == text_lower or (kw.lower() in text_lower and len(text_lower) <= 60):
                return True
        return False

    def find_header_row(self, table: List[List[str]]) -> int:
        """
        智能识别表头行位置

        通过打分机制判断哪一行最可能是表头：
        - 包含表头特征词（part/number/型号/电容等）+5分
        - 纯字母且长度<=8（可能是简写表头）+3分

        Args:
            table: 表格数据

        Returns:
            表头行的索引（从0开始）
        """
        if not table or len(table) < 2:
            return 0

        best_score = 0
        best_row = 0

        # 只检查前10行
        for row_idx, row in enumerate(table[:min(10, len(table))]):
            score = 0
            cell_count = 0
            for cell in row:
                cell_str = str(cell).strip().lower()
                if cell_str:
                    cell_count += 1
                    # 表头特征词匹配
                    if any(kw in cell_str for kw in ['part', 'number', '型号', '规格', 'item', '项目', '特性', 'cap', 'voltage', '电容', '尺寸', 'series', 'code', '编码', 'wv', 'ur', 'catalog', 'size']):
                        score += 5
                    # 纯字母简写匹配
                    if re.match(r'^[a-zA-Z]+$', cell_str) and len(cell_str) <= 8:
                        score += 3
            # 至少有2个非空单元格且分数最高
            if cell_count >= 2 and score > best_score:
                best_score = score
                best_row = row_idx

        return best_row

    def find_header_rows(self, table: List[List[str]]) -> Tuple[int, int]:
        """
        识别多行表头的范围

        有些表格表头可能跨多行（如合并单元格），此方法找出表头的起始行和结束行。

        改进点：
        1. 增加更多表头特征词检测
        2. 检测首字母大写的文本（通常是表头）
        3. 检测单位符号和括号内的说明
        4. 检测表头关键词的部分匹配（如"part"在"catalog part number"中）

        Args:
            table: 表格数据

        Returns:
            (起始行索引, 结束行索引)
        """
        start_row = self.find_header_row(table)

        end_row = start_row
        # 检查后续最多8行是否仍包含表头特征（增加检查行数）
        check_end = min(start_row + 3, len(table))
        
        # 收集已确认的表头关键词（用于后续行的判断）
        header_keywords_found = set()
        for cell in table[start_row]:
            cell_str = str(cell).strip().lower()
            if cell_str:
                for kw in ['part', 'number', 'cap', 'voltage', 'size', 'catalog', 'series', 'tolerance', 'code', '型号', '编码', '电容', '电压', '尺寸', '公差', '系列']:
                    if kw in cell_str:
                        header_keywords_found.add(kw)

        for row_idx in range(start_row + 1, check_end):
            row = table[row_idx]
            has_header_like = False
            
            for cell in row:
                cell_str = str(cell).strip()
                if not cell_str:
                    continue
                    
                cell_lower = cell_str.lower()
                
                # 检测1：表头特征词匹配
                if any(kw in cell_lower for kw in ['part', 'number', 'cap', 'voltage', 'size', 'tan', 'esr', 'catalog', 'series', 'tolerance', 'code', '型号', '编码', '电容', '电压', '尺寸', '公差', '系列', 'wv', 'ur']):
                    has_header_like = True
                    break
                
                # 检测2：首字母大写且长度适中（通常是表头）
                if cell_str and cell_str[0].isupper() and len(cell_str) <= 50:
                    # 排除纯数字或产品型号（如HSE102M51）
                    if not re.match(r'^[A-Z0-9]+$', cell_str):
                        has_header_like = True
                        break
                
                # 检测3：包含单位符号
                if any(unit in cell_lower for unit in ['μf', 'mm', 'v', 'ω', 'mhz', 'pf', 'nf', 'ohm']):
                    has_header_like = True
                    break
                
                # 检测4：包含括号或括号内的说明
                if '(' in cell_str or ')' in cell_str or '（' in cell_str or '）' in cell_str:
                    has_header_like = True
                    break
                
                # 检测5：匹配已确认的表头关键词的部分
                if header_keywords_found:
                    for kw in header_keywords_found:
                        if kw in cell_lower:
                            has_header_like = True
                            break
            
            if has_header_like:
                end_row = row_idx
            else:
                break

        return start_row, end_row

    def build_merged_header(self, table: List[List[str]], start_row: int, end_row: int) -> List[str]:
        """
        将多行表头合并为单行表头

        对于跨多行的表头，将同一列的多个表头单元格合并为一个完整的表头名称。

        Args:
            table: 表格数据
            start_row: 表头起始行
            end_row: 表头结束行

        Returns:
            合并后的单行表头列表
        """
        if not table or start_row > end_row:
            return []

        num_cols = len(table[start_row]) if table else 0
        merged_header = [""] * num_cols

        for row_idx in range(start_row, end_row + 1):
            row = table[row_idx]
            for col_idx, cell in enumerate(row):
                cell_str = str(cell).strip()
                if cell_str:
                    if merged_header[col_idx]:
                        merged_header[col_idx] += " " + cell_str
                    else:
                        merged_header[col_idx] = cell_str

        return merged_header

    def search_header(self, table: List[List[str]], keyword: str) -> Optional[int]:
        """
        先字典后泛化的表头搜索策略

        搜索流程：
        1. 如果关键词在KEYWORD_RULES字典中，优先使用字典中的同义词列表进行匹配
        2. 如果字典匹配失败，使用泛化搜索（关键词包含在表头文本中）
        3. 返回匹配到的列索引

        Args:
            table: 表格数据
            keyword: 搜索关键词

        Returns:
            匹配到的列索引，未找到返回None
        """
        if not table or not keyword:
            return None

        keyword_lower = keyword.lower().strip()
        if not keyword_lower:
            return None

        start_row, end_row = self.find_header_rows(table)

        # 第一层：字典搜索（精确匹配同义词）
        if keyword_lower in self.KEYWORD_RULES:
            rules = self.KEYWORD_RULES[keyword_lower]
            keywords = rules['keywords']

            for row_idx in range(start_row, min(end_row + 2, len(table))):
                row = table[row_idx]
                for col_idx, cell in enumerate(row):
                    if self._contains_keyword(cell, keywords):
                        return col_idx

        # 第二层：泛化搜索（模糊匹配）
        for row_idx in range(start_row, min(end_row + 2, len(table))):
            row = table[row_idx]
            for col_idx, cell in enumerate(row):
                cell_str = str(cell).strip().lower()
                if not cell_str:
                    continue

                # 关键词包含在表头中，或表头包含在关键词中
                if keyword_lower in cell_str or cell_str in keyword_lower:
                    return col_idx

        return None

    def search_all_headers(self, table: List[List[str]], keywords: List[str]) -> Dict[str, int]:
        """
        批量搜索多个关键词对应的表头列

        Args:
            table: 表格数据
            keywords: 关键词列表

        Returns:
            关键词到列索引的映射字典
        """
        mapping = {}
        used_cols = set()

        for keyword in keywords:
            col_idx = self.search_header(table, keyword)
            # 确保同一列不会被多个关键词匹配
            if col_idx is not None and col_idx not in used_cols:
                mapping[keyword] = col_idx
                used_cols.add(col_idx)

        return mapping


class PDFTableExtractor:
    """
    PDF表格提取器（核心类）

    集成PyMuPDF和OCR两种提取方式，提供表格提取和关键词搜索功能。
    支持大文件处理和多页批量搜索。
    """

    def __init__(self, pdf_path: str, use_ocr: bool = True):
        """
        初始化PDF表格提取器

        Args:
            pdf_path: PDF文件路径
            use_ocr: 是否启用OCR回退，默认True
        """
        self.pdf_path = pdf_path
        self.use_ocr = use_ocr
        self.ocr_extractor = None
        self.structure_analyzer = TableStructureAnalyzer()
        self.keyword_searcher = KeywordSearcher()
        self._all_cells = {}  # OCR识别结果缓存

    def _init_ocr_if_needed(self):
        """延迟初始化OCR（只在需要时创建）"""
        if self.use_ocr and self.ocr_extractor is None:
            self.ocr_extractor = OCRTableExtractor()

    def _get_ocr_cells(self, page_num: int) -> List[Dict]:
        """
        获取指定页面的OCR识别结果（带缓存）

        Args:
            page_num: 页码

        Returns:
            单元格列表
        """
        if page_num not in self._all_cells:
            self._init_ocr_if_needed()
            if self.ocr_extractor:
                cells = self.ocr_extractor.recognize_from_pdf_page(self.pdf_path, page_num)
                self._all_cells[page_num] = cells
            else:
                self._all_cells[page_num] = []
        return self._all_cells[page_num]

    def _is_scanned_pdf(self, page_num: int) -> bool:
        """
        检测PDF页面是否为扫描件（图片型PDF）
        
        Args:
            page_num: 页码
            
        Returns:
            True表示扫描件，False表示文本型PDF
        """
        doc = fitz.open(self.pdf_path)
        page = doc.load_page(page_num)
        
        text = page.get_text()
        blocks = page.get_text("blocks")
        
        text_block_count = sum(1 for b in blocks if b[6] == 0)
        
        doc.close()
        
        if text_block_count < 5 or len(text.strip()) < 20:
            return True
        return False

    def _save_page_image(self, page_num: int) -> str:
        pdf_dir = os.path.dirname(self.pdf_path)
        pdf_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        image_dir = os.path.join(pdf_dir, f"{pdf_name}_扫描图片")
        os.makedirs(image_dir, exist_ok=True)
        
        doc = fitz.open(self.pdf_path)
        page = doc.load_page(page_num)
        
        is_scanned = self._is_scanned_pdf(page_num)
        if is_scanned:
            pix = page.get_pixmap(matrix=fitz.Matrix(4.0, 4.0))
        else:
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        
        image_path = os.path.join(image_dir, f"page_{page_num + 1}.png")
        pix.save(image_path)
        doc.close()
        
        return image_path

    def _is_valid_table(self, table: List[List[str]]) -> bool:
        if not table or len(table) < 2:
            return False
        col_count = len(table[0])
        if col_count < 2:
            return False
        valid_cols = 0
        for row in table[:5]:
            if len(row) >= col_count:
                non_empty = sum(1 for cell in row if cell and str(cell).strip())
                if non_empty >= 2:
                    valid_cols += 1
        return valid_cols >= 2

    def extract_tables(self, page_num: int = 0) -> List[List[List[str]]]:
        """
        提取指定页面的表格数据

        提取策略：
        1. 保存页面截图到文件夹
        2. 检测是否为扫描件
        3. 非扫描件：优先使用PyMuPDF，失败再OCR
        4. 扫描件：优先使用OCR，失败再PPStructure
        5. 验证表格有效性后输出

        Args:
            page_num: 页码（从0开始）

        Returns:
            表格数据列表，每个表格是一个二维列表
        """
        self._save_page_image(page_num)
        
        is_scanned = self._is_scanned_pdf(page_num)
        
        if not is_scanned:
            tables = self._extract_with_pymupdf(page_num)
            
            all_tables = []
            for table in tables:
                split_tables = self.structure_analyzer.split_double_table(table)
                for t in split_tables:
                    if self._is_valid_table(t):
                        all_tables.append(t)
            
            if all_tables:
                return all_tables
            
            if self.use_ocr:
                self._init_ocr_if_needed()
                if self.ocr_extractor:
                    tables = self._extract_with_ocr(page_num)
                    valid_tables = [t for t in tables if self._is_valid_table(t)]
                    if valid_tables:
                        return valid_tables
            
            return []
        else:
            if self.use_ocr:
                self._init_ocr_if_needed()
                if self.ocr_extractor:
                    tables = self._extract_with_ocr(page_num)
                    valid_tables = [t for t in tables if self._is_valid_table(t)]
                    if valid_tables:
                        return valid_tables
                    
                    image_path = os.path.join(
                        os.path.dirname(self.pdf_path),
                        f"{os.path.splitext(os.path.basename(self.pdf_path))[0]}_扫描图片",
                        f"page_{page_num + 1}.png"
                    )
                    tables = self.ocr_extractor.recognize_table_with_ppstructure(image_path)
                    valid_tables = [t for t in tables if isinstance(t, list) and self._is_valid_table(t)]
                    if valid_tables:
                        return valid_tables
            
            return []
    def _extract_with_pymupdf(self, page_num: int) -> List[List[List[str]]]:
        """
        使用PyMuPDF提取表格

        PyMuPDF提供了find_tables()方法，可以快速识别PDF中的表格结构。

        Args:
            page_num: 页码

        Returns:
            表格数据列表
        """
        doc = fitz.open(self.pdf_path)
        page = doc.load_page(page_num)

        tables = []
        try:
            # 使用PyMuPDF的表格识别功能
            tabs = page.find_tables()
            for tab in tabs.tables:
                table_data = []
                for row in tab.extract():
                    table_data.append([str(cell).strip() if cell else "" for cell in row])
                # 过滤无效表格（至少2行2列）
                if table_data and len(table_data) >= 2 and len(table_data[0]) >= 2:
                    # 不在这里清洗，而是在 split_double_table 中统一处理
                    # 避免在分割前删除可能只在一侧有数据的行
                    tables.append(table_data)
        except Exception:
            pass

        return tables

    def _extract_with_ocr(self, page_num: int) -> List[List[List[str]]]:
        """
        使用OCR提取表格

        当PyMuPDF无法识别表格时，使用OCR进行文字识别，然后通过坐标聚类重建表格结构。

        Args:
            page_num: 页码

        Returns:
            表格数据列表
        """
        # 获取OCR识别结果
        cells = self._get_ocr_cells(page_num)

        if not cells:
            print("OCR识别结果为空")
            return []

        # 按Y坐标聚类，识别行
        rows = self._cluster_by_rows(cells, y_tolerance=35)

        if len(rows) < 2:
            return []

        # 检测列位置
        column_x = self._detect_columns(rows)

        if len(column_x) < 2:
            return []

        # 根据列位置重建表格
        table = []
        for row in rows:
            row_data = [""] * len(column_x)
            for cell in row:
                # 找到距离最近的列
                min_dist = float('inf')
                min_idx = 0
                for j, x in enumerate(column_x):
                    dist = abs(cell["center_x"] - x)
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = j

                # 同一列有多个单元格时合并
                if row_data[min_idx]:
                    row_data[min_idx] += " " + cell["text"]
                else:
                    row_data[min_idx] = cell["text"]
            table.append(row_data)

        cleaned = self.structure_analyzer.clean_table(table)
        if len(cleaned) >= 2:
            return [cleaned]

        return []

    def _cluster_by_rows(self, cells: List[Dict], y_tolerance: int = 35) -> List[List[Dict]]:
        """
        按Y坐标聚类单元格，识别表格行

        Args:
            cells: 单元格列表（带坐标信息）
            y_tolerance: Y坐标容差（像素）

        Returns:
            行列表，每行包含该行的所有单元格
        """
        if not cells:
            return []

        # 按Y坐标排序，然后按X坐标排序
        sorted_cells = sorted(cells, key=lambda c: (c["y0"], c["x0"]))

        rows = []
        current_row = [sorted_cells[0]]
        current_y_center = sorted_cells[0]["center_y"]

        for cell in sorted_cells[1:]:
            # Y坐标差异在容差范围内属于同一行
            if abs(cell["center_y"] - current_y_center) < y_tolerance:
                current_row.append(cell)
            else:
                rows.append(current_row)
                current_row = [cell]
                current_y_center = cell["center_y"]

        if current_row:
            rows.append(current_row)

        # 每行内部按X坐标排序
        for row in rows:
            row.sort(key=lambda c: c["x0"])

        return rows

    def _detect_columns(self, rows: List[List[Dict]]) -> List[float]:
        """
        检测表格列位置

        通过对所有单元格的X中心坐标进行聚类，确定列的位置。

        Args:
            rows: 行列表

        Returns:
            列中心X坐标列表（已排序）
        """
        if not rows:
            return []

        x_positions = []
        for row in rows:
            for cell in row:
                x_positions.append(cell["center_x"])

        x_positions.sort()

        if not x_positions:
            return []

        # X坐标聚类，距离小于80像素的归为同一列
        clusters = []
        current_cluster = [x_positions[0]]

        for x in x_positions[1:]:
            if x - current_cluster[-1] < 80:
                current_cluster.append(x)
            else:
                clusters.append(current_cluster)
                current_cluster = [x]

        if current_cluster:
            clusters.append(current_cluster)

        # 计算每个聚类的中心坐标作为列位置
        column_x = [sum(c) / len(c) for c in clusters]
        return sorted(column_x)

    def search_by_keyword(self, page_num: int, keywords: List[str]) -> Dict[str, Any]:
        """
        在指定页面搜索包含关键词的数据

        搜索流程：
        1. 提取页面中的所有表格
        2. 对每个表格识别表头行并合并
        3. 搜索关键词对应的表头列
        4. 提取匹配列下方的数据行

        Args:
            page_num: 页码
            keywords: 关键词列表

        Returns:
            搜索结果字典，包含页码、表格数量、匹配数据等信息
        """
        tables = self.extract_tables(page_num)

        results = {
            "page": page_num,
            "tables_found": len(tables),
            "results": []
        }

        for table_idx, table in enumerate(tables):
            # 识别表头行范围并合并
            start_row, end_row = self.keyword_searcher.find_header_rows(table)
            merged_header = self.keyword_searcher.build_merged_header(table, start_row, end_row)

            # 搜索所有关键词对应的列
            header_mapping = self.keyword_searcher.search_all_headers(table, keywords)

            if header_mapping:
                table_result = {
                    "table_index": table_idx,
                    "total_rows": len(table),
                    "header_start_row": start_row,
                    "header_end_row": end_row,
                    "header_mapping": header_mapping,
                    "headers": merged_header,
                    "data": []
                }

                # 提取表头行和数据行（包含表头行，让用户可以自己判断）
                for row_idx, row in enumerate(table):
                    # 从表头起始行开始，包含表头行
                    if row_idx < start_row:
                        continue

                    row_data = {}
                    has_valid_data = False
                    
                    # 提取搜索关键词对应的列数据
                    for keyword, col_idx in header_mapping.items():
                        value = row[col_idx] if col_idx < len(row) else ""
                        row_data[keyword] = value
                        if str(value).strip():
                            has_valid_data = True

                    # 检查整行是否有任何数据（不仅仅是搜索列）
                    # 确保所有有数据的行都被保留
                    if not has_valid_data:
                        for cell in row:
                            if str(cell).strip():
                                has_valid_data = True
                                break

                    # 添加来源信息
                    row_data["_source_row"] = row_idx
                    row_data["_source_table"] = table_idx
                    row_data["_is_header"] = "是" if row_idx <= end_row else "否"

                    # 只保留包含有效数据的行
                    if has_valid_data:
                        table_result["data"].append(row_data)

                results["results"].append(table_result)

        return results

    def search_in_all_pages(self, keywords: List[str]) -> Dict[str, Any]:
        """
        在PDF所有页面搜索包含关键词的数据

        Args:
            keywords: 关键词列表

        Returns:
            全文档搜索结果
        """
        doc = fitz.open(self.pdf_path)
        total_pages = doc.page_count
        doc.close()

        all_results = {
            "total_pages": total_pages,
            "results": []
        }

        for page_num in range(total_pages):
            page_results = self.search_by_keyword(page_num, keywords)
            if page_results["results"]:
                all_results["results"].append(page_results)

        return all_results


def main(pdf_path: str, keywords: List[str], page_num: int = 0) -> pd.DataFrame:
    """
    主函数：提取表格数据并返回DataFrame

    Args:
        pdf_path: PDF文件路径
        keywords: 关键词列表
        page_num: 页码，默认0

    Returns:
        包含匹配数据的DataFrame
    """
    extractor = PDFTableExtractor(pdf_path, use_ocr=True)
    results = extractor.search_by_keyword(page_num, keywords)

    all_data = []
    for table_result in results["results"]:
        for row in table_result["data"]:
            row_copy = row.copy()
            row_copy["_来源表格"] = table_result["table_index"]
            row_copy["_来源行号"] = row_copy.get("_source_row", "")
            all_data.append(row_copy)

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)

    # 按关键词顺序排列列，最后显示来源信息
    cols_order = [k for k in keywords if k in df.columns]
    cols_order.extend(["_来源行号", "_来源表格"])

    return df[cols_order]


if __name__ == "__main__":
    """测试入口"""
    import os

    pdf_path = os.path.join("最新目录PDF", "AJ.pdf")
    keywords = ["partnumber", "cap", "wv"]

    print("=" * 60)
    print("PDF 表格数据提取器 - 测试")
    print("=" * 60)

    extractor = PDFTableExtractor(pdf_path, use_ocr=True)

    doc = fitz.open(pdf_path)
    total_pages = doc.page_count

    # 测试表格提取
    for page_num in range(total_pages):
        tables = extractor.extract_tables(page_num)
        print(f"\n--- 第 {page_num + 1} 页 ---")
        print(f"识别到 {len(tables)} 个表格")

        for i, table in enumerate(tables):
            start_row, end_row = extractor.keyword_searcher.find_header_rows(table)
            merged_header = extractor.keyword_searcher.build_merged_header(table, start_row, end_row)
            print(f"\n表格 {i+1}: {len(table)}行 x {len(table[0])}列")
            print(f"表头行范围: {start_row}-{end_row}")
            print("合并表头:", merged_header)

    print("\n" + "=" * 60)
    print(f"搜索关键词: {keywords}")
    print("=" * 60)

    # 测试关键词搜索
    for page_num in range(total_pages):
        results = extractor.search_by_keyword(page_num, keywords)
        if results["results"]:
            print(f"\n--- 第 {page_num + 1} 页 ---")
            for table_result in results["results"]:
                print(f"\n表格 {table_result['table_index']}:")
                print(f"  表头映射: {table_result['header_mapping']}")
                print(f"  找到 {len(table_result['data'])} 行数据")

    # 测试DataFrame输出
    df = main(pdf_path, keywords, page_num=1)
    print(f"\n最终 DataFrame ({len(df)} 行):")
    print(df)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)