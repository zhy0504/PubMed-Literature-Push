import pandas as pd
import os
import logging
import re

class DataProcessor:
    """
    负责加载和处理 zky.csv 和 jcr.csv 文件，并提供数据匹配功能。
    """
    def __init__(self, zky_path='zky.csv', jcr_path='jcr.csv'):
        self.zky_db = self._load_zky_data(zky_path)
        self.jcr_db = self._load_jcr_data(jcr_path)

    def _load_zky_data(self, path):
        """加载并预处理中科院分区数据，自动处理列名大小写。"""
        if not os.path.exists(path):
            logging.warning(f"中科院分区文件 '{path}' 未找到，相关数据将为空。")
            return {}
        
        logging.info(f"正在加载中科院分区文件: {path}")
        df = pd.read_csv(path)
        df.columns = [col.strip().lower() for col in df.columns] # 列名小写化

        required_cols = ['issn/eissn', '大类分区', 'top', '小类1分区']
        if not all(col in df.columns for col in required_cols):
            logging.error(f"'{path}' 文件缺少必要列。需要: {required_cols}, 实际拥有: {list(df.columns)}")
            return {}

        db = {}
        for _, row in df.iterrows():
            issn_eissn_str = str(row.get('issn/eissn', ''))
            issn_eissn = issn_eissn_str.split('/')
            issn = issn_eissn[0].strip()
            eissn = issn_eissn[1].strip() if len(issn_eissn) > 1 else None
            
            data = {
                '大类分区': row['大类分区'],
                'Top': row['top'],
                '小类1分区': row['小类1分区']
            }
            if issn: db[issn] = data
            if eissn: db[eissn] = data
        
        logging.info(f"中科院分区数据加载完毕，共 {len(db)} 条记录。")
        return db

    def _load_jcr_data(self, path):
        """加载并预处理 JCR 影响因子数据，动态处理年份和列名大小写。"""
        if not os.path.exists(path):
            logging.warning(f"JCR 数据文件 '{path}' 未找到，相关数据将为空。")
            return {}
            
        logging.info(f"正在加载 JCR 数据文件: {path}")
        df = pd.read_csv(path)
        df.columns = [col.strip().lower() for col in df.columns]

        if 'issn' not in df.columns or 'eissn' not in df.columns:
            logging.error(f"'{path}' 文件缺少 'issn' 或 'eissn' 列。")
            return {}

        # 动态查找 IF 和 IF Quartile 列
        if_col = next((col for col in df.columns if re.match(r'if\(\d{4}\)', col)), None)
        quartile_col = next((col for col in df.columns if re.match(r'if quartile\(\d{4}\)', col)), None)
        
        if not if_col: logging.warning(f"在 '{path}' 中未找到影响因子列 (例如 'if(2024)')。")
        if not quartile_col: logging.warning(f"在 '{path}' 中未找到影响因子分区列 (例如 'if quartile(2024)')。")

        db = {}
        for _, row in df.iterrows():
            issn = str(row.get('issn', '')).strip()
            eissn = str(row.get('eissn', '')).strip()
            
            data = {}
            if if_col and pd.notna(row[if_col]):
                data['IF'] = row[if_col]
            if quartile_col and pd.notna(row[quartile_col]):
                data['IF Quartile'] = row[quartile_col]

            if not data: continue

            if issn and issn != 'nan': db[issn] = data
            if eissn and eissn != 'nan': db[eissn] = data
            
        logging.info(f"JCR 数据加载完毕，共 {len(db)} 条记录。")
        return db

    def get_zky_data(self, issn: str, eissn: str) -> dict:
        """根据 ISSN 或 EISSN 获取中科院分区数据。"""
        return self.zky_db.get(issn) or self.zky_db.get(eissn, {})

    def get_jcr_data(self, issn: str, eissn: str) -> dict:
        """根据 ISSN 或 EISSN 获取 JCR 数据。"""
        return self.jcr_db.get(issn) or self.jcr_db.get(eissn, {})

if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    # 假设 zky.csv 和 jcr.csv 在项目根目录
    processor = DataProcessor()
    
    # 示例测试
    test_issn = "0028-0836" # Nature
    zky_data = processor.get_zky_data(test_issn, "")
    jcr_data = processor.get_jcr_data(test_issn, "")
    
    print(f"\n测试 ISSN: {test_issn}")
    print("中科院数据:", zky_data)
    print("JCR 数据:", jcr_data)