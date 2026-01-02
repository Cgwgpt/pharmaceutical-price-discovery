"""
Scrapy数据处理管道
实现数据清洗、验证和数据库存储逻辑
"""
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from config import DATABASE_URL
from app.models import Drug, PriceRecord, init_db


logger = logging.getLogger(__name__)


class DataCleaningPipeline:
    """
    数据清洗管道
    
    负责清洗和标准化爬取的数据：
    - 去除多余空格
    - 清洗价格字符串
    - 标准化规格单位
    """
    
    def process_item(self, item, spider):
        """
        处理并清洗数据项
        
        Args:
            item: DrugItem数据项
            spider: 爬虫实例
            
        Returns:
            清洗后的item
        """
        adapter = ItemAdapter(item)
        
        # 清洗药品名称
        name = adapter.get('name', '')
        adapter['name'] = self._clean_name(name)
        
        # 清洗价格
        price = adapter.get('price', '')
        adapter['price'] = self._clean_price(price)
        
        # 清洗规格
        specification = adapter.get('specification', '')
        adapter['specification'] = self._clean_specification(specification)
        
        # 清洗其他字段
        for field in ['dosage_form', 'manufacturer', 'source_name']:
            value = adapter.get(field, '')
            if value:
                adapter[field] = self._clean_text(value)
        
        return item
    
    def _clean_name(self, name: str) -> str:
        """
        清洗药品名称
        
        - 去除首尾空格
        - 将多个连续空格替换为单个空格
        - 移除特殊字符（保留中文、字母、数字、括号）
        """
        if not name:
            return ''
        
        # 去除首尾空格
        name = name.strip()
        
        # 将多个连续空格替换为单个空格
        name = re.sub(r'\s+', ' ', name)
        
        # 移除特殊字符，保留中文、字母、数字、括号、空格
        name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\(\)（）\-]', '', name)
        
        return name
    
    def _clean_price(self, price: str) -> str:
        """
        清洗价格字符串
        
        提取数字部分，支持格式如：
        - ¥12.50
        - 12.50元
        - 12.5
        """
        if not price:
            return ''
        
        # 移除货币符号和单位
        price = re.sub(r'[¥￥元]', '', price)
        
        # 去除空格
        price = price.strip()
        
        # 提取数字（包括小数点）
        match = re.search(r'(\d+\.?\d*)', price)
        if match:
            return match.group(1)
        
        return ''
    
    def _clean_specification(self, spec: str) -> str:
        """
        清洗规格字符串
        
        标准化单位格式
        """
        if not spec:
            return ''
        
        spec = spec.strip()
        
        # 标准化单位（按顺序处理，先处理复合单位）
        spec = re.sub(r'(?i)ml', 'ml', spec)  # 先处理ml
        spec = re.sub(r'(?i)mg', 'mg', spec)  # 再处理mg
        spec = re.sub(r'(?i)(?<!m)g(?!m)', 'g', spec)  # g但不是mg的一部分
        spec = re.sub(r'(?i)(?<!m)l(?!m)', 'L', spec)  # L但不是ml的一部分
        
        return spec
    
    def _clean_text(self, text: str) -> str:
        """通用文本清洗"""
        if not text:
            return ''
        return re.sub(r'\s+', ' ', text.strip())


class ValidationPipeline:
    """
    数据验证管道
    
    验证必填字段是否存在且有效
    """
    
    # 通用价格范围（最小值，最大值）- 只做基本范围校验
    PRICE_RANGE = (0.01, 100000)
    
    # 是否只保留药品（False 表示允许化妆品、医疗器械等入库）
    DRUG_ONLY = False
    
    def process_item(self, item, spider):
        """
        验证数据项
        
        Args:
            item: DrugItem数据项
            spider: 爬虫实例
            
        Returns:
            验证通过的item
            
        Raises:
            DropItem: 验证失败时抛出
        """
        adapter = ItemAdapter(item)
        
        # 验证必填字段
        name = adapter.get('name', '')
        if not name:
            raise DropItem("缺少药品名称")
        
        price = adapter.get('price', '')
        if not price:
            raise DropItem(f"缺少价格信息: {name}")
        
        # 验证价格是否为有效数字
        try:
            price_decimal = Decimal(price)
            if price_decimal <= 0:
                raise DropItem(f"价格必须大于0: {name}")
        except InvalidOperation:
            raise DropItem(f"无效的价格格式: {price}")
        
        # 基本价格范围校验
        price_float = float(price_decimal)
        if price_float < self.PRICE_RANGE[0] or price_float > self.PRICE_RANGE[1]:
            raise DropItem(f"价格超出合理范围: {name} ¥{price}")
        
        # 规格校验 - 必须有规格信息
        specification = adapter.get('specification', '').strip()
        if not specification:
            raise DropItem(f"缺少规格信息: {name}")
        
        # 产品类别过滤
        category = adapter.get('category', 'drug')
        if self.DRUG_ONLY and category not in ['drug']:
            raise DropItem(f"非药品类别 ({category}): {name}")
        
        # 厂家校验 - 必须有有效厂家
        manufacturer = adapter.get('manufacturer', '').strip()
        if not manufacturer or manufacturer in ['未知厂家', '未知', '-', 'None']:
            raise DropItem(f"缺少有效厂家信息: {name}")
        
        source_url = adapter.get('source_url', '')
        if not source_url:
            raise DropItem(f"缺少来源URL: {name}")
        
        source_name = adapter.get('source_name', '')
        if not source_name:
            raise DropItem(f"缺少来源网站名称: {name}")
        
        return item


class DatabasePipeline:
    """
    数据库存储管道
    
    将清洗和验证后的数据保存到数据库
    """
    
    def __init__(self):
        self.session = None
        self.engine = None
    
    def open_spider(self, spider):
        """
        爬虫启动时初始化数据库连接
        """
        try:
            self.engine, SessionLocal = init_db(DATABASE_URL)
            self.session = SessionLocal()
            logger.info("数据库连接已建立")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def close_spider(self, spider):
        """
        爬虫关闭时关闭数据库连接
        """
        if self.session:
            self.session.close()
            logger.info("数据库连接已关闭")
    
    def process_item(self, item, spider):
        """
        将数据项保存到数据库
        
        Args:
            item: DrugItem数据项
            spider: 爬虫实例
            
        Returns:
            处理后的item
        """
        adapter = ItemAdapter(item)
        
        try:
            # 查找或创建药品记录
            drug = self._get_or_create_drug(adapter)
            
            # 创建价格记录
            self._create_price_record(drug, adapter)
            
            self.session.commit()
            logger.info(f"已保存: {adapter.get('name')} - ¥{adapter.get('price')}")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"保存数据失败: {e}")
            raise
        
        return item
    
    def _get_or_create_drug(self, adapter: ItemAdapter) -> Drug:
        """
        获取或创建药品记录
        
        Args:
            adapter: ItemAdapter实例
            
        Returns:
            Drug: 药品记录
        """
        name = adapter.get('name')
        specification = adapter.get('specification', '')
        
        # 尝试查找现有药品
        drug = self.session.query(Drug).filter(
            Drug.name == name,
            Drug.specification == specification
        ).first()
        
        if not drug:
            # 创建新药品记录
            drug = Drug(
                name=name,
                standard_name=name,  # 初始时标准名称与名称相同
                specification=specification,
                dosage_form=adapter.get('dosage_form', ''),
                manufacturer=adapter.get('manufacturer', ''),
                approval_number=adapter.get('approval_number', ''),
                category=adapter.get('category', 'drug')
            )
            self.session.add(drug)
            self.session.flush()  # 获取ID
            logger.info(f"创建新药品记录: {name}")
        else:
            # 更新批准文号和类别（如果之前没有）
            if not drug.approval_number and adapter.get('approval_number'):
                drug.approval_number = adapter.get('approval_number')
            if not drug.category or drug.category == 'drug':
                drug.category = adapter.get('category', 'drug')
        
        return drug
    
    def _create_price_record(self, drug: Drug, adapter: ItemAdapter) -> PriceRecord:
        """
        创建价格记录
        
        Args:
            drug: 药品记录
            adapter: ItemAdapter实例
            
        Returns:
            PriceRecord: 价格记录
        """
        price_record = PriceRecord(
            drug_id=drug.id,
            price=Decimal(adapter.get('price')),
            source_url=adapter.get('source_url'),
            source_name=adapter.get('source_name')
        )
        self.session.add(price_record)
        return price_record
