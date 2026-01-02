"""
数据标准化服务
实现药品名称标准化、规格单位标准化和药品标识生成
"""
import re
import hashlib
from typing import Optional, Dict, List, Tuple
from functools import lru_cache


class NormalizeService:
    """
    药品数据标准化服务
    
    功能:
    - 药品名称清洗和标准化
    - 规格单位标准化
    - 药品唯一标识生成
    - 别名映射管理
    - 同药不同名识别
    """
    
    # 常见药品名称前缀（品牌名）
    BRAND_PREFIXES = [
        '999', '三九', '同仁堂', '云南白药', '修正', '哈药', '华润',
        '太极', '康恩贝', '白云山', '仁和', '葵花', '江中', '东阿',
        '片仔癀', '马应龙', '以岭', '步长', '天士力', '扬子江',
    ]
    
    # 常见药品别名映射（通用名 -> 别名列表）
    DRUG_ALIASES = {
        '阿莫西林': ['阿莫仙', '阿莫灵', '弗莱莫星', '再林'],
        '布洛芬': ['芬必得', '美林', '恬倩', '托恩'],
        '对乙酰氨基酚': ['扑热息痛', '泰诺林', '必理通', '百服宁'],
        '头孢克洛': ['希刻劳', '可福乐', '头孢克洛干混悬剂'],
        '头孢氨苄': ['先锋霉素IV', '头孢力新'],
        '氯雷他定': ['开瑞坦', '克敏能', '百为坦'],
        '西替利嗪': ['仙特明', '西可韦', '斯特林'],
        '奥美拉唑': ['洛赛克', '奥克', '奥美'],
        '阿奇霉素': ['希舒美', '泰力特', '维宏'],
        '左氧氟沙星': ['可乐必妥', '利复星', '来立信'],
        '甲硝唑': ['灭滴灵', '甲硝唑片'],
        '维生素C': ['维C', 'VC', '抗坏血酸'],
        '维生素B': ['维B', 'VB', '复合维生素B'],
        '葡萄糖': ['右旋糖', 'Glucose'],
        '氯化钠': ['生理盐水', '盐水'],
    }
    
    # 构建反向别名映射
    ALIAS_TO_GENERIC = {}
    for generic, aliases in DRUG_ALIASES.items():
        for alias in aliases:
            ALIAS_TO_GENERIC[alias.lower()] = generic
        ALIAS_TO_GENERIC[generic.lower()] = generic
    
    # 规格单位标准化映射
    UNIT_MAPPINGS = {
        # 重量单位
        'mg': ['毫克', 'MG', 'milligram', 'milligrams'],
        'g': ['克', 'G', 'gram', 'grams'],
        'kg': ['千克', 'KG', 'kilogram', 'kilograms'],
        'μg': ['微克', 'ug', 'UG', 'mcg', 'MCG'],
        # 容量单位
        'ml': ['毫升', 'ML', 'mL', 'milliliter', 'milliliters'],
        'L': ['升', 'l', 'liter', 'liters'],
        # 数量单位
        '片': ['片剂', 'tab', 'tabs', 'tablet', 'tablets'],
        '粒': ['颗', '颗粒'],
        '袋': ['包', 'bag', 'bags', 'sachet'],
        '支': ['枝', 'amp', 'amps', 'ampoule'],
        '瓶': ['bottle', 'bottles'],
        '盒': ['box', 'boxes'],
    }
    
    # 剂型标准化映射
    DOSAGE_FORM_MAPPINGS = {
        '片剂': ['片', '薄膜衣片', '糖衣片', '肠溶片', '缓释片', '控释片', '分散片', '咀嚼片', '泡腾片', '口崩片'],
        '胶囊剂': ['胶囊', '硬胶囊', '软胶囊', '肠溶胶囊', '缓释胶囊'],
        '颗粒剂': ['颗粒', '冲剂', '干混悬剂'],
        '口服液': ['口服溶液', '糖浆', '合剂', '酊剂', '滴剂'],
        '注射剂': ['注射液', '注射用', '粉针', '水针', '冻干粉'],
        '外用剂': ['软膏', '乳膏', '凝胶', '贴剂', '喷雾剂', '滴眼液', '滴鼻液', '栓剂'],
    }
    
    def __init__(self):
        # 构建反向映射
        self._unit_reverse_map = self._build_reverse_map(self.UNIT_MAPPINGS)
        self._dosage_reverse_map = self._build_reverse_map(self.DOSAGE_FORM_MAPPINGS)
    
    def _build_reverse_map(self, mappings: Dict[str, List[str]]) -> Dict[str, str]:
        """构建反向映射字典"""
        reverse_map = {}
        for standard, variants in mappings.items():
            for variant in variants:
                reverse_map[variant.lower()] = standard
            reverse_map[standard.lower()] = standard
        return reverse_map
    
    def normalize_name(self, name: str) -> str:
        """
        标准化药品名称
        
        处理步骤:
        1. 去除首尾空格
        2. 统一全角/半角字符
        3. 去除多余空格
        4. 移除特殊字符
        5. 提取通用名（去除品牌前缀）
        
        Args:
            name: 原始药品名称
            
        Returns:
            标准化后的名称
        """
        if not name:
            return ''
        
        # 去除首尾空格
        name = name.strip()
        
        # 全角转半角
        name = self._full_to_half(name)
        
        # 统一空格
        name = re.sub(r'\s+', ' ', name)
        
        # 移除特殊字符，保留中文、字母、数字、括号、空格、连字符
        name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\(\)（）\-\.]', '', name)
        
        # 统一括号
        name = name.replace('（', '(').replace('）', ')')
        
        return name
    
    def extract_generic_name(self, name: str) -> Tuple[str, Optional[str]]:
        """
        提取通用名和品牌名
        
        Args:
            name: 药品名称
            
        Returns:
            (通用名, 品牌名) 元组
        """
        normalized = self.normalize_name(name)
        
        # 检查是否有品牌前缀
        brand = None
        generic = normalized
        
        for prefix in self.BRAND_PREFIXES:
            if normalized.startswith(prefix):
                brand = prefix
                generic = normalized[len(prefix):].strip()
                break
            # 检查空格分隔的品牌名
            if normalized.startswith(prefix + ' '):
                brand = prefix
                generic = normalized[len(prefix)+1:].strip()
                break
        
        return generic, brand
    
    def normalize_specification(self, spec: str) -> str:
        """
        标准化规格字符串
        
        处理步骤:
        1. 清洗空格
        2. 标准化单位
        3. 统一格式
        
        Args:
            spec: 原始规格字符串
            
        Returns:
            标准化后的规格
        """
        if not spec:
            return ''
        
        spec = spec.strip()
        
        # 全角转半角
        spec = self._full_to_half(spec)
        
        # 标准化单位
        for standard, variants in self.UNIT_MAPPINGS.items():
            for variant in variants:
                # 使用单词边界匹配，避免部分替换
                pattern = re.compile(re.escape(variant), re.IGNORECASE)
                spec = pattern.sub(standard, spec)
        
        # 统一乘号
        spec = re.sub(r'[×xX\*]', '*', spec)
        
        # 移除多余空格
        spec = re.sub(r'\s+', '', spec)
        
        return spec
    
    def normalize_unit(self, unit: str) -> str:
        """
        标准化单位
        
        Args:
            unit: 原始单位
            
        Returns:
            标准化后的单位
        """
        if not unit:
            return ''
        
        unit_lower = unit.strip().lower()
        return self._unit_reverse_map.get(unit_lower, unit.strip())
    
    def normalize_dosage_form(self, dosage_form: str) -> str:
        """
        标准化剂型
        
        Args:
            dosage_form: 原始剂型
            
        Returns:
            标准化后的剂型
        """
        if not dosage_form:
            return ''
        
        form_lower = dosage_form.strip().lower()
        
        # 直接匹配
        if form_lower in self._dosage_reverse_map:
            return self._dosage_reverse_map[form_lower]
        
        # 模糊匹配
        for standard, variants in self.DOSAGE_FORM_MAPPINGS.items():
            for variant in variants:
                if variant in dosage_form:
                    return standard
        
        return dosage_form.strip()
    
    def _full_to_half(self, text: str) -> str:
        """全角字符转半角"""
        result = []
        for char in text:
            code = ord(char)
            # 全角空格
            if code == 0x3000:
                result.append(' ')
            # 其他全角字符
            elif 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            else:
                result.append(char)
        return ''.join(result)
    
    @lru_cache(maxsize=10000)
    def generate_drug_id(self, name: str, specification: str = '', manufacturer: str = '') -> str:
        """
        生成药品唯一标识
        
        基于标准化后的名称、规格和厂家生成唯一ID
        
        Args:
            name: 药品名称
            specification: 规格
            manufacturer: 生产厂家
            
        Returns:
            唯一标识字符串
        """
        # 标准化各字段
        norm_name = self.normalize_name(name)
        generic_name, _ = self.extract_generic_name(norm_name)
        norm_spec = self.normalize_specification(specification)
        norm_mfr = self.normalize_name(manufacturer)
        
        # 组合生成哈希
        combined = f"{generic_name}|{norm_spec}|{norm_mfr}"
        hash_obj = hashlib.md5(combined.encode('utf-8'))
        
        return hash_obj.hexdigest()[:16]
    
    def generate_simple_id(self, name: str, specification: str = '') -> str:
        """
        生成简化药品标识（不含厂家）
        
        用于同一药品不同厂家的匹配
        
        Args:
            name: 药品名称
            specification: 规格
            
        Returns:
            简化标识字符串
        """
        norm_name = self.normalize_name(name)
        generic_name, _ = self.extract_generic_name(norm_name)
        norm_spec = self.normalize_specification(specification)
        
        combined = f"{generic_name}|{norm_spec}"
        hash_obj = hashlib.md5(combined.encode('utf-8'))
        
        return hash_obj.hexdigest()[:12]
    
    def is_same_drug(self, drug1: Dict, drug2: Dict) -> bool:
        """
        判断两个药品是否为同一药品
        
        Args:
            drug1: 药品1信息字典
            drug2: 药品2信息字典
            
        Returns:
            是否为同一药品
        """
        id1 = self.generate_simple_id(
            drug1.get('name', ''),
            drug1.get('specification', '')
        )
        id2 = self.generate_simple_id(
            drug2.get('name', ''),
            drug2.get('specification', '')
        )
        return id1 == id2
    
    def normalize_drug_data(self, drug_data: Dict) -> Dict:
        """
        标准化完整的药品数据
        
        Args:
            drug_data: 原始药品数据字典
            
        Returns:
            标准化后的药品数据
        """
        normalized = drug_data.copy()
        
        # 标准化名称
        if 'name' in normalized:
            normalized['name'] = self.normalize_name(normalized['name'])
            generic, brand = self.extract_generic_name(normalized['name'])
            normalized['generic_name'] = generic
            normalized['brand_name'] = brand
        
        # 标准化规格
        if 'specification' in normalized:
            normalized['specification'] = self.normalize_specification(normalized['specification'])
        
        # 标准化剂型
        if 'dosage_form' in normalized:
            normalized['dosage_form'] = self.normalize_dosage_form(normalized['dosage_form'])
        
        # 标准化厂家
        if 'manufacturer' in normalized:
            normalized['manufacturer'] = self.normalize_name(normalized['manufacturer'])
        
        # 生成标识
        normalized['drug_id'] = self.generate_drug_id(
            normalized.get('name', ''),
            normalized.get('specification', ''),
            normalized.get('manufacturer', '')
        )
        normalized['simple_id'] = self.generate_simple_id(
            normalized.get('name', ''),
            normalized.get('specification', '')
        )
        
        return normalized

    
    def get_generic_name(self, name: str) -> str:
        """
        获取药品通用名（处理别名）
        
        Args:
            name: 药品名称（可能是别名）
            
        Returns:
            通用名
        """
        normalized = self.normalize_name(name)
        
        # 先提取通用名（去除品牌）
        generic, _ = self.extract_generic_name(normalized)
        
        # 检查是否是已知别名
        generic_lower = generic.lower()
        if generic_lower in self.ALIAS_TO_GENERIC:
            return self.ALIAS_TO_GENERIC[generic_lower]
        
        # 模糊匹配别名
        for alias, generic_name in self.ALIAS_TO_GENERIC.items():
            if alias in generic_lower or generic_lower in alias:
                return generic_name
        
        return generic
    
    def find_similar_drugs(self, name: str, drugs: List[Dict]) -> List[Dict]:
        """
        查找相似药品（同药不同名）
        
        Args:
            name: 药品名称
            drugs: 药品列表
            
        Returns:
            相似药品列表
        """
        target_generic = self.get_generic_name(name)
        similar = []
        
        for drug in drugs:
            drug_generic = self.get_generic_name(drug.get('name', ''))
            
            # 通用名相同
            if drug_generic == target_generic:
                drug['match_type'] = 'generic_match'
                drug['generic_name'] = drug_generic
                similar.append(drug)
                continue
            
            # 简化ID相同（名称+规格）
            if drug.get('specification'):
                target_id = self.generate_simple_id(name, '')
                drug_id = self.generate_simple_id(drug.get('name', ''), '')
                
                if target_id == drug_id:
                    drug['match_type'] = 'id_match'
                    similar.append(drug)
                    continue
            
            # 名称相似度匹配
            similarity = self._calculate_similarity(target_generic, drug_generic)
            if similarity > 0.7:
                drug['match_type'] = 'similarity_match'
                drug['similarity'] = similarity
                similar.append(drug)
        
        return similar
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """
        计算两个字符串的相似度
        
        使用Jaccard相似度
        """
        if not s1 or not s2:
            return 0.0
        
        set1 = set(s1)
        set2 = set(s2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def merge_drug_records(self, drugs: List[Dict]) -> List[Dict]:
        """
        合并同药不同名的记录
        
        Args:
            drugs: 药品列表
            
        Returns:
            合并后的药品列表
        """
        # 按通用名分组
        groups = {}
        
        for drug in drugs:
            generic = self.get_generic_name(drug.get('name', ''))
            spec = self.normalize_specification(drug.get('specification', ''))
            key = f"{generic}|{spec}"
            
            if key not in groups:
                groups[key] = {
                    'generic_name': generic,
                    'specification': spec,
                    'variants': [],
                    'prices': []
                }
            
            groups[key]['variants'].append(drug.get('name', ''))
            if drug.get('price'):
                groups[key]['prices'].append({
                    'price': drug['price'],
                    'source': drug.get('source_name', ''),
                    'name': drug.get('name', '')
                })
        
        # 转换为列表
        result = []
        for key, group in groups.items():
            prices = group['prices']
            if prices:
                prices.sort(key=lambda x: x['price'])
                lowest = prices[0]
                highest = prices[-1]
            else:
                lowest = highest = None
            
            result.append({
                'generic_name': group['generic_name'],
                'specification': group['specification'],
                'variant_names': list(set(group['variants'])),
                'variant_count': len(set(group['variants'])),
                'price_count': len(prices),
                'lowest_price': lowest['price'] if lowest else None,
                'lowest_source': lowest['source'] if lowest else None,
                'highest_price': highest['price'] if highest else None,
                'highest_source': highest['source'] if highest else None,
                'all_prices': prices
            })
        
        return result
    
    def add_alias(self, generic_name: str, alias: str):
        """
        添加药品别名
        
        Args:
            generic_name: 通用名
            alias: 别名
        """
        alias_lower = alias.lower()
        generic_lower = generic_name.lower()
        
        # 添加到别名映射
        if generic_name not in self.DRUG_ALIASES:
            self.DRUG_ALIASES[generic_name] = []
        
        if alias not in self.DRUG_ALIASES[generic_name]:
            self.DRUG_ALIASES[generic_name].append(alias)
        
        # 更新反向映射
        self.ALIAS_TO_GENERIC[alias_lower] = generic_name
    
    def get_all_aliases(self, generic_name: str) -> List[str]:
        """
        获取药品的所有别名
        
        Args:
            generic_name: 通用名
            
        Returns:
            别名列表
        """
        return self.DRUG_ALIASES.get(generic_name, [])
