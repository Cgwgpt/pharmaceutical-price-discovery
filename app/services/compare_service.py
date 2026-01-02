"""
比价服务
实现多平台价格比较、排序和价差计算

比价逻辑：
1. 同一产品比价：相同药品名称 + 相同规格 + 相同厂家 → 比较不同供应商价格
2. 可替代产品参考：相同药品名称 + 相同规格，不同厂家 → 替代选择参考
"""
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from config import DATABASE_URL
from app.models import Drug, PriceRecord, init_db
from app.services.normalize_service import NormalizeService


class CompareService:
    """
    比价服务
    
    功能:
    - 同一产品比价（相同名称+规格+厂家）
    - 可替代产品参考（相同名称+规格，不同厂家）
    - 价格排序（最低价优先）
    - 价差百分比计算
    - 潜在节省金额计算
    """
    
    # 非药品关键词（化妆品、保健品等）
    NON_DRUG_KEYWORDS = [
        '珍珠霜', '珍珠膏', '护肤', '面霜', '乳液', '精华', '面膜',
        '洗面奶', '洁面', '化妆', '美白', '防晒', '口红', '眼霜',
        '沐浴', '洗发', '护发', '香水', '彩妆', '粉底', '眼影',
        '牙膏', '漱口水', '卫生巾', '纸尿裤', '湿巾',
        '保健食品', '营养品', '蛋白粉', '维生素片',
    ]
    
    def __init__(self):
        self.engine, SessionLocal = init_db(DATABASE_URL)
        self.session = SessionLocal()
        self.normalize_service = NormalizeService()
    
    def _is_drug_product(self, drug_name: str, manufacturer: str = None) -> bool:
        """
        判断是否为药品（排除化妆品等非药品）
        
        Args:
            drug_name: 药品名称
            manufacturer: 厂家名称
            
        Returns:
            True 如果是药品，False 如果是非药品
        """
        full_text = f"{drug_name} {manufacturer or ''}"
        
        for keyword in self.NON_DRUG_KEYWORDS:
            if keyword in full_text:
                return False
        
        # 检查厂家是否为化妆品公司
        cosmetic_manufacturers = ['化妆品', '日化', '美容']
        if manufacturer:
            for keyword in cosmetic_manufacturers:
                if keyword in manufacturer:
                    return False
        
        return True
    
    def __del__(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()
    
    def compare_prices(self, drug_name: str, specification: str = None, category: str = None) -> Optional[Dict[str, Any]]:
        """
        比较同一药品在不同平台的价格（支持两层比价）
        
        Args:
            drug_name: 药品名称（可包含规格信息）
            specification: 规格（可选，用于精确匹配）
            category: 产品类别过滤（drug=药品, cosmetic=化妆品, medical_device=医疗器械）
            
        Returns:
            比价结果字典，包含：
            - products: 按厂家分组的产品列表
            - alternatives: 可替代产品参考（同通用名不同厂家）
        """
        import re
        
        # 从搜索词中提取药品名和规格
        # 例如 "片仔癀 3g*1粒(RX)" -> 药品名="片仔癀", 规格="3g*1粒"
        search_name = drug_name
        search_spec = specification
        
        # 尝试从搜索词中分离规格信息
        spec_pattern = r'(\d+[gml]*\*?\d*[粒片袋支盒瓶]*)'
        spec_match = re.search(spec_pattern, drug_name, re.IGNORECASE)
        if spec_match and not specification:
            search_spec = spec_match.group(1)
            # 提取药品名（规格之前的部分）
            search_name = drug_name[:spec_match.start()].strip()
            if not search_name:
                search_name = drug_name
        
        # 标准化搜索词
        normalized_name = self.normalize_service.normalize_name(search_name)
        
        # 如果标准化后为空，直接使用原名
        if not normalized_name:
            normalized_name = search_name
        
        # 查找匹配的药品
        query = self.session.query(Drug).filter(
            Drug.name.ilike(f'%{normalized_name}%')
        )
        
        # 如果有规格，也按规格过滤
        if search_spec:
            # 清理规格中的特殊字符用于搜索
            clean_spec = re.sub(r'[（）\(\)]', '', search_spec)
            query = query.filter(Drug.specification.ilike(f'%{clean_spec}%'))
        
        # 按类别过滤
        if category:
            query = query.filter(Drug.category == category)
        
        drugs = query.all()
        
        if not drugs:
            return None
        
        # 如果没有指定类别，自动按类别分组，只返回同类别的产品
        if not category:
            # 统计各类别数量
            category_counts = {}
            for d in drugs:
                cat = d.category or 'drug'
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            # 优先选择药品类别，如果有药品就选药品
            if 'drug' in category_counts:
                main_category = 'drug'
            else:
                # 否则选数量最多的类别
                main_category = max(category_counts, key=category_counts.get)
            
            # 只保留主要类别的产品
            drugs = [d for d in drugs if (d.category or 'drug') == main_category]
        
        if not drugs:
            return None
        
        # 按"通用名+规格+厂家"分组
        products_by_key = {}  # key: (通用名, 规格, 厂家)
        
        for drug in drugs:
            # 提取通用名
            common_name = self._extract_common_name(drug.name)
            spec = drug.specification or ''
            manufacturer = drug.manufacturer or '未知厂家'
            
            key = (common_name, spec, manufacturer)
            
            if key not in products_by_key:
                products_by_key[key] = {
                    'common_name': common_name,
                    'specification': spec,
                    'manufacturer': manufacturer,
                    'drugs': [],
                    'prices': []
                }
            
            products_by_key[key]['drugs'].append(drug)
            
            # 获取该药品的价格
            prices = self._get_latest_prices_by_source(drug.id)
            for p in prices:
                p['drug_name'] = drug.name
                p['drug_id'] = drug.id
                p['specification'] = drug.specification
                p['manufacturer'] = manufacturer
                p['common_name'] = common_name
            products_by_key[key]['prices'].extend(prices)
        
        # 按"通用名+规格"分组（相同规格才能比价）
        products_by_spec = {}  # key: (通用名, 规格)
        all_prices = []
        
        for key, product in products_by_key.items():
            if not product['prices']:
                continue
            
            common_name = product['common_name']
            spec = product['specification']
            spec_key = (common_name, spec)
            
            # 按价格排序
            product['prices'].sort(key=lambda x: x['price'])
            
            # 计算该产品的统计信息
            price_values = [p['price'] for p in product['prices']]
            min_price = min(price_values)
            max_price = max(price_values)
            
            product_info = {
                'common_name': common_name,
                'specification': spec,
                'manufacturer': product['manufacturer'],
                'min_price': round(min_price, 2),
                'max_price': round(max_price, 2),
                'price_diff': round(max_price - min_price, 2),
                'price_diff_percent': round((max_price - min_price) / min_price * 100, 2) if min_price > 0 else 0,
                'supplier_count': len(product['prices']),
                'prices': product['prices']
            }
            
            # 按"通用名+规格"分组
            if spec_key not in products_by_spec:
                products_by_spec[spec_key] = {
                    'common_name': common_name,
                    'specification': spec,
                    'manufacturers': []
                }
            products_by_spec[spec_key]['manufacturers'].append(product_info)
            
            all_prices.extend(product['prices'])
        
        if not products_by_spec:
            return None
        
        # 构建按规格分组的结果
        product_groups = []
        for spec_key, group in products_by_spec.items():
            # 按最低价排序厂家
            group['manufacturers'].sort(key=lambda x: x['min_price'])
            
            # 标记最优选择
            if group['manufacturers']:
                group['manufacturers'][0]['is_best_choice'] = True
                for p in group['manufacturers'][1:]:
                    p['is_best_choice'] = False
            
            # 计算该规格的统计
            all_prices_in_group = []
            for m in group['manufacturers']:
                all_prices_in_group.extend([p['price'] for p in m['prices']])
            
            group_info = {
                'common_name': group['common_name'],
                'specification': group['specification'],
                'display_name': f"{group['common_name']} {group['specification']}",
                'manufacturers': group['manufacturers'],
                'manufacturer_count': len(group['manufacturers']),
                'best_price': group['manufacturers'][0]['min_price'] if group['manufacturers'] else 0,
                'best_manufacturer': group['manufacturers'][0]['manufacturer'] if group['manufacturers'] else None,
                'min_price': min(all_prices_in_group) if all_prices_in_group else 0,
                'max_price': max(all_prices_in_group) if all_prices_in_group else 0,
            }
            product_groups.append(group_info)
        
        # 按最优价格排序产品组
        product_groups.sort(key=lambda x: x['best_price'])
        
        # 标记所有价格中的最低价
        if all_prices:
            all_prices.sort(key=lambda x: x['price'])
            all_prices[0]['is_lowest'] = True
            for p in all_prices[1:]:
                p['is_lowest'] = False
        
        # 获取当前比价的产品类别
        current_category = drugs[0].category if drugs else 'drug'
        
        # 计算整体统计
        result = self._calculate_comparison_stats_v3(drug_name, product_groups, all_prices)
        if result:
            result['category'] = current_category
            result['category_name'] = {
                'drug': '药品',
                'cosmetic': '化妆品',
                'medical_device': '医疗器械',
                'other': '其他'
            }.get(current_category, '药品')
        return result
    
    def _extract_common_name(self, drug_name: str) -> str:
        """
        提取药品通用名（去掉品牌前缀，保留完整药品名）
        
        例如：
        - "石药 CSPC石药集团 阿莫西林胶囊 0.25g*24粒" → "阿莫西林胶囊"
        - "999 感冒灵颗粒 10g*9袋" → "感冒灵颗粒"
        - "奥先 阿莫西林克拉维酸钾片(7:1) 1.0g*6片" → "阿莫西林克拉维酸钾片"
        """
        import re
        
        # 常见的药品剂型后缀
        dosage_forms = [
            '肠溶胶囊', '缓释胶囊', '软胶囊', '胶囊',
            '缓释片', '分散片', '咀嚼片', '泡腾片', '肠溶片', '片',
            '颗粒', '冲剂', '散',
            '口服液', '口服溶液', '糖浆', '合剂', '酊',
            '注射液', '注射用', '粉针',
            '滴丸', '丸', '丹',
            '乳膏', '软膏', '凝胶', '霜', '膏',
            '栓', '贴', '贴剂', '贴膏',
            '喷雾剂', '气雾剂', '吸入剂',
            '滴眼液', '眼膏', '滴耳液',
            '溶液', '洗剂', '搽剂'
        ]
        
        # 按长度排序，优先匹配更长的剂型
        dosage_forms.sort(key=len, reverse=True)
        
        # 尝试找到剂型后缀
        for form in dosage_forms:
            if form in drug_name:
                # 找到剂型位置
                idx = drug_name.find(form)
                end_idx = idx + len(form)
                
                # 向前查找药品名开始位置
                # 跳过品牌名、空格等
                start = idx
                
                # 向前扫描，找到中文药品名的开始
                while start > 0:
                    prev_char = drug_name[start - 1]
                    # 如果是中文字符，继续向前
                    if '\u4e00' <= prev_char <= '\u9fff':
                        start -= 1
                    # 如果是空格或特殊字符，停止
                    elif prev_char in ' 　()（）':
                        break
                    # 如果是英文或数字，可能是规格，停止
                    elif prev_char.isalnum():
                        break
                    else:
                        break
                
                common_name = drug_name[start:end_idx].strip()
                
                # 清理可能的前缀
                # 去掉开头的数字和特殊字符
                common_name = re.sub(r'^[\d\s\-\.]+', '', common_name)
                
                if common_name and len(common_name) >= 2:
                    return common_name
        
        # 如果没找到剂型，尝试提取中文部分
        chinese_parts = re.findall(r'[\u4e00-\u9fff]+', drug_name)
        if chinese_parts:
            # 返回最长的中文部分
            return max(chinese_parts, key=len)
        
        # 如果都没找到，返回原名
        return drug_name
    
    def _calculate_comparison_stats_v3(self, drug_name: str, product_groups: List[Dict], all_prices: List[Dict]) -> Dict[str, Any]:
        """
        计算比价统计信息（按规格分组版本）
        
        Args:
            drug_name: 搜索的药品名称
            product_groups: 按规格分组的产品列表
            all_prices: 所有价格列表
        """
        if not all_prices:
            return None
        
        price_values = [p['price'] for p in all_prices]
        lowest = min(price_values)
        highest = max(price_values)
        average = sum(price_values) / len(price_values)
        
        # 价差百分比
        diff_percent = ((highest - lowest) / lowest * 100) if lowest > 0 else 0
        
        # 潜在节省
        potential_savings = highest - lowest
        
        # 统计厂家总数
        total_manufacturers = sum(g['manufacturer_count'] for g in product_groups)
        
        # 扁平化产品列表（兼容旧模板）
        flat_products = []
        for group in product_groups:
            flat_products.extend(group['manufacturers'])
        
        return {
            'drug_name': drug_name,
            'product_groups': product_groups,  # 按规格分组
            'products': flat_products,  # 扁平化列表（兼容旧接口）
            'prices': all_prices,  # 所有价格
            'lowest_price': round(lowest, 2),
            'highest_price': round(highest, 2),
            'average_price': round(average, 2),
            'price_diff_percent': round(diff_percent, 2),
            'potential_savings': round(potential_savings, 2),
            'spec_count': len(product_groups),  # 规格数量
            'manufacturer_count': total_manufacturers,  # 厂家总数
            'total_records': len(all_prices),
            'best_spec': product_groups[0]['display_name'] if product_groups else None,
            'best_manufacturer': product_groups[0]['best_manufacturer'] if product_groups else None,
            'best_price': product_groups[0]['best_price'] if product_groups else None,
            'compared_at': datetime.now().isoformat()
        }
    
    def _calculate_comparison_stats_v2(self, drug_name: str, products_by_common_name: Dict, all_prices: List[Dict]) -> Dict[str, Any]:
        """
        计算比价统计信息（新版本，支持按通用名分组）
        
        Args:
            drug_name: 搜索的药品名称
            products_by_common_name: 按通用名分组的产品字典
            all_prices: 所有价格列表
        """
        if not all_prices:
            return None
        
        price_values = [p['price'] for p in all_prices]
        lowest = min(price_values)
        highest = max(price_values)
        average = sum(price_values) / len(price_values)
        
        # 价差百分比
        diff_percent = ((highest - lowest) / lowest * 100) if lowest > 0 else 0
        
        # 潜在节省
        potential_savings = highest - lowest
        
        # 构建产品分组列表
        product_groups = []
        total_manufacturers = 0
        
        for common_name, products in products_by_common_name.items():
            group = {
                'common_name': common_name,
                'manufacturers': products,
                'manufacturer_count': len(products),
                'best_price': products[0]['min_price'] if products else 0,
                'best_manufacturer': products[0]['manufacturer'] if products else None
            }
            product_groups.append(group)
            total_manufacturers += len(products)
        
        # 按最优价格排序产品组
        product_groups.sort(key=lambda x: x['best_price'])
        
        # 扁平化产品列表（兼容旧模板）
        flat_products = []
        for group in product_groups:
            flat_products.extend(group['manufacturers'])
        
        return {
            'drug_name': drug_name,
            'product_groups': product_groups,  # 按通用名分组
            'products': flat_products,  # 扁平化列表（兼容旧接口）
            'prices': all_prices,  # 所有价格
            'lowest_price': round(lowest, 2),
            'highest_price': round(highest, 2),
            'average_price': round(average, 2),
            'price_diff_percent': round(diff_percent, 2),
            'potential_savings': round(potential_savings, 2),
            'common_name_count': len(product_groups),  # 通用名数量（不同药品）
            'manufacturer_count': total_manufacturers,  # 厂家总数
            'total_records': len(all_prices),
            'best_common_name': product_groups[0]['common_name'] if product_groups else None,
            'best_manufacturer': product_groups[0]['best_manufacturer'] if product_groups else None,
            'best_price': product_groups[0]['best_price'] if product_groups else None,
            'compared_at': datetime.now().isoformat()
        }
    
    def _get_latest_prices_by_source(self, drug_id: int) -> List[Dict[str, Any]]:
        """
        获取药品在各平台的最新价格
        
        Args:
            drug_id: 药品ID
            
        Returns:
            价格列表
        """
        # 子查询：每个来源的最新记录
        subquery = (
            self.session.query(
                PriceRecord.source_name,
                func.max(PriceRecord.crawled_at).label('max_time')
            )
            .filter(PriceRecord.drug_id == drug_id)
            .group_by(PriceRecord.source_name)
            .subquery()
        )
        
        # 获取最新价格
        records = (
            self.session.query(PriceRecord)
            .join(
                subquery,
                (PriceRecord.source_name == subquery.c.source_name) &
                (PriceRecord.crawled_at == subquery.c.max_time)
            )
            .filter(PriceRecord.drug_id == drug_id)
            .all()
        )
        
        return [
            {
                'id': r.id,
                'price': float(r.price),
                'source_name': r.source_name,
                'source_url': r.source_url,
                'crawled_at': r.crawled_at.isoformat() if r.crawled_at else None
            }
            for r in records
        ]
    
    def _calculate_comparison_stats(self, drug_name: str, prices: List[Dict]) -> Dict[str, Any]:
        """
        计算比价统计信息
        
        Args:
            drug_name: 药品名称
            prices: 价格列表
            
        Returns:
            比价结果
        """
        price_values = [p['price'] for p in prices]
        lowest = min(price_values)
        highest = max(price_values)
        average = sum(price_values) / len(price_values)
        
        # 价差百分比 = (最高价 - 最低价) / 最低价 * 100
        diff_percent = ((highest - lowest) / lowest * 100) if lowest > 0 else 0
        
        # 潜在节省 = 最高价 - 最低价
        potential_savings = highest - lowest
        
        # 按来源分组统计
        source_stats = {}
        for p in prices:
            source = p['source_name']
            if source not in source_stats:
                source_stats[source] = {
                    'count': 0,
                    'min_price': float('inf'),
                    'max_price': 0,
                    'total': 0
                }
            source_stats[source]['count'] += 1
            source_stats[source]['min_price'] = min(source_stats[source]['min_price'], p['price'])
            source_stats[source]['max_price'] = max(source_stats[source]['max_price'], p['price'])
            source_stats[source]['total'] += p['price']
        
        for source in source_stats:
            source_stats[source]['avg_price'] = round(
                source_stats[source]['total'] / source_stats[source]['count'], 2
            )
        
        return {
            'drug_name': drug_name,
            'prices': prices,
            'lowest_price': round(lowest, 2),
            'highest_price': round(highest, 2),
            'average_price': round(average, 2),
            'price_diff_percent': round(diff_percent, 2),
            'potential_savings': round(potential_savings, 2),
            'source_count': len(set(p['source_name'] for p in prices)),
            'total_records': len(prices),
            'source_stats': source_stats,
            'best_source': prices[0]['source_name'] if prices else None,
            'compared_at': datetime.now().isoformat()
        }
    
    def compare_by_simple_id(self, simple_id: str) -> Optional[Dict[str, Any]]:
        """
        通过简化标识比较价格（同药不同厂家）
        
        Args:
            simple_id: 简化药品标识
            
        Returns:
            比价结果
        """
        drugs = self.session.query(Drug).filter(
            Drug.simple_hash == simple_id
        ).all()
        
        if not drugs:
            return None
        
        all_prices = []
        for drug in drugs:
            prices = self._get_latest_prices_by_source(drug.id)
            for p in prices:
                p['drug_name'] = drug.name
                p['drug_id'] = drug.id
                p['specification'] = drug.specification
                p['manufacturer'] = drug.manufacturer
                all_prices.append(p)
        
        if not all_prices:
            return None
        
        all_prices.sort(key=lambda x: x['price'])
        
        if all_prices:
            all_prices[0]['is_lowest'] = True
            for p in all_prices[1:]:
                p['is_lowest'] = False
        
        return self._calculate_comparison_stats(drugs[0].name, all_prices)
    
    def calculate_price_diff(self, price1: float, price2: float) -> Dict[str, float]:
        """
        计算两个价格之间的差异
        
        Args:
            price1: 价格1
            price2: 价格2
            
        Returns:
            差异信息
        """
        if price1 <= 0 or price2 <= 0:
            return {'diff': 0, 'diff_percent': 0, 'savings': 0}
        
        diff = abs(price1 - price2)
        base_price = min(price1, price2)
        diff_percent = (diff / base_price) * 100
        
        return {
            'diff': round(diff, 2),
            'diff_percent': round(diff_percent, 2),
            'savings': round(diff, 2),
            'lower_price': round(min(price1, price2), 2),
            'higher_price': round(max(price1, price2), 2)
        }
    
    def calculate_batch_savings(self, drug_name: str, quantity: int) -> Optional[Dict[str, Any]]:
        """
        计算批量采购的潜在节省
        
        Args:
            drug_name: 药品名称
            quantity: 采购数量
            
        Returns:
            节省金额信息
        """
        comparison = self.compare_prices(drug_name)
        
        if not comparison or comparison['source_count'] < 2:
            return None
        
        unit_savings = comparison['potential_savings']
        total_savings = unit_savings * quantity
        
        lowest_total = comparison['lowest_price'] * quantity
        highest_total = comparison['highest_price'] * quantity
        
        return {
            'drug_name': drug_name,
            'quantity': quantity,
            'unit_lowest_price': comparison['lowest_price'],
            'unit_highest_price': comparison['highest_price'],
            'unit_savings': round(unit_savings, 2),
            'total_lowest_cost': round(lowest_total, 2),
            'total_highest_cost': round(highest_total, 2),
            'total_savings': round(total_savings, 2),
            'savings_percent': comparison['price_diff_percent'],
            'best_source': comparison['best_source']
        }
    
    def get_price_ranking(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取价差最大的药品排名
        
        Args:
            limit: 返回数量
            
        Returns:
            排名列表
        """
        # 获取所有有多个来源的药品
        drugs_with_multiple_sources = (
            self.session.query(Drug.id, Drug.name)
            .join(PriceRecord)
            .group_by(Drug.id)
            .having(func.count(func.distinct(PriceRecord.source_name)) > 1)
            .all()
        )
        
        rankings = []
        for drug_id, drug_name in drugs_with_multiple_sources:
            comparison = self.compare_prices(drug_name)
            if comparison and comparison['price_diff_percent'] > 0:
                rankings.append({
                    'drug_id': drug_id,
                    'drug_name': drug_name,
                    'lowest_price': comparison['lowest_price'],
                    'highest_price': comparison['highest_price'],
                    'diff_percent': comparison['price_diff_percent'],
                    'potential_savings': comparison['potential_savings'],
                    'best_source': comparison['best_source']
                })
        
        # 按价差百分比排序
        rankings.sort(key=lambda x: x['diff_percent'], reverse=True)
        
        return rankings[:limit]
