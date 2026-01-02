"""
属性测试 - 使用Hypothesis进行属性测试
"""
import pytest
from decimal import Decimal
from hypothesis import given, strategies as st, settings
from scrapy.exceptions import DropItem

from app.models import Drug, PriceRecord, Base
from scraper.items import DrugItem
from scraper.pipelines import DataCleaningPipeline, ValidationPipeline
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# 自定义策略：生成有效的药品名称
drug_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' -'),
    min_size=1,
    max_size=100
).filter(lambda x: x.strip() != '')

# 自定义策略：生成有效的价格（正数，最多2位小数）
price_strategy = st.decimals(
    min_value=Decimal('0.01'),
    max_value=Decimal('99999.99'),
    places=2,
    allow_nan=False,
    allow_infinity=False
)

# 自定义策略：生成有效的URL
url_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='/:.-_'),
    min_size=10,
    max_size=200
).map(lambda x: f'https://example.com/{x}')

# 自定义策略：生成有效的来源名称
source_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=' '),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() != '')


@pytest.fixture
def property_session():
    """为属性测试创建独立的数据库会话"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


class TestDataExtractionCompleteness:
    """
    Feature: pharmaceutical-price-discovery
    Property 1: 数据提取完整性
    Validates: Requirements 1.2, 2.1
    
    对于任意有效的药品网页内容，爬虫提取的DrugItem应当包含非空的
    name、price、source_url和source_name字段。
    """
    
    # 生成清洗后仍有效的药品名称（只包含中文、字母、数字、空格、括号、连字符）
    valid_drug_name_strategy = st.text(
        alphabet=st.sampled_from('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -()'),
        min_size=1,
        max_size=50
    ).filter(lambda x: x.strip() != '' and any(c.isalnum() for c in x))

    @given(
        name=valid_drug_name_strategy,
        price=price_strategy,
        source_url=url_strategy,
        source_name=source_name_strategy
    )
    @settings(max_examples=100)
    def test_valid_drug_item_passes_validation(self, name, price, source_url, source_name):
        """
        Feature: pharmaceutical-price-discovery
        Property 1: 数据提取完整性
        Validates: Requirements 1.2, 2.1
        
        测试有效的DrugItem通过验证管道后包含所有必填字段
        """
        # 创建DrugItem
        item = DrugItem()
        item['name'] = name
        item['price'] = str(price)
        item['source_url'] = source_url
        item['source_name'] = source_name
        
        # 通过数据清洗管道
        cleaning_pipeline = DataCleaningPipeline()
        cleaned_item = cleaning_pipeline.process_item(item, spider=None)
        
        # 通过验证管道
        validation_pipeline = ValidationPipeline()
        validated_item = validation_pipeline.process_item(cleaned_item, spider=None)
        
        # 验证所有必填字段非空
        assert validated_item.get('name'), "name字段应当非空"
        assert validated_item.get('price'), "price字段应当非空"
        assert validated_item.get('source_url'), "source_url字段应当非空"
        assert validated_item.get('source_name'), "source_name字段应当非空"

    @given(
        valid_name=drug_name_strategy,
        valid_price=price_strategy,
        valid_url=url_strategy,
        valid_source=source_name_strategy
    )
    @settings(max_examples=100)
    def test_invalid_item_missing_name_rejected(self, valid_name, valid_price, valid_url, valid_source):
        """
        Feature: pharmaceutical-price-discovery
        Property 1: 数据提取完整性
        Validates: Requirements 1.2, 2.1
        
        测试缺少name字段的DrugItem被验证管道拒绝
        """
        # 创建缺少name的DrugItem
        item = DrugItem()
        item['name'] = ''  # 空名称
        item['price'] = str(valid_price)
        item['source_url'] = valid_url
        item['source_name'] = valid_source
        
        # 通过数据清洗管道
        cleaning_pipeline = DataCleaningPipeline()
        cleaned_item = cleaning_pipeline.process_item(item, spider=None)
        
        # 验证管道应当拒绝该item
        validation_pipeline = ValidationPipeline()
        with pytest.raises(DropItem):
            validation_pipeline.process_item(cleaned_item, spider=None)

    @given(
        valid_name=drug_name_strategy,
        valid_url=url_strategy,
        valid_source=source_name_strategy
    )
    @settings(max_examples=100)
    def test_invalid_item_missing_price_rejected(self, valid_name, valid_url, valid_source):
        """
        Feature: pharmaceutical-price-discovery
        Property 1: 数据提取完整性
        Validates: Requirements 1.2, 2.1
        
        测试缺少price字段的DrugItem被验证管道拒绝
        """
        # 创建缺少price的DrugItem
        item = DrugItem()
        item['name'] = valid_name
        item['price'] = ''  # 空价格
        item['source_url'] = valid_url
        item['source_name'] = valid_source
        
        # 通过数据清洗管道
        cleaning_pipeline = DataCleaningPipeline()
        cleaned_item = cleaning_pipeline.process_item(item, spider=None)
        
        # 验证管道应当拒绝该item
        validation_pipeline = ValidationPipeline()
        with pytest.raises(DropItem):
            validation_pipeline.process_item(cleaned_item, spider=None)

    @given(
        valid_name=drug_name_strategy,
        valid_price=price_strategy,
        valid_source=source_name_strategy
    )
    @settings(max_examples=100)
    def test_invalid_item_missing_source_url_rejected(self, valid_name, valid_price, valid_source):
        """
        Feature: pharmaceutical-price-discovery
        Property 1: 数据提取完整性
        Validates: Requirements 1.2, 2.1
        
        测试缺少source_url字段的DrugItem被验证管道拒绝
        """
        # 创建缺少source_url的DrugItem
        item = DrugItem()
        item['name'] = valid_name
        item['price'] = str(valid_price)
        item['source_url'] = ''  # 空URL
        item['source_name'] = valid_source
        
        # 通过数据清洗管道
        cleaning_pipeline = DataCleaningPipeline()
        cleaned_item = cleaning_pipeline.process_item(item, spider=None)
        
        # 验证管道应当拒绝该item
        validation_pipeline = ValidationPipeline()
        with pytest.raises(DropItem):
            validation_pipeline.process_item(cleaned_item, spider=None)

    @given(
        valid_name=drug_name_strategy,
        valid_price=price_strategy,
        valid_url=url_strategy
    )
    @settings(max_examples=100)
    def test_invalid_item_missing_source_name_rejected(self, valid_name, valid_price, valid_url):
        """
        Feature: pharmaceutical-price-discovery
        Property 1: 数据提取完整性
        Validates: Requirements 1.2, 2.1
        
        测试缺少source_name字段的DrugItem被验证管道拒绝
        """
        # 创建缺少source_name的DrugItem
        item = DrugItem()
        item['name'] = valid_name
        item['price'] = str(valid_price)
        item['source_url'] = valid_url
        item['source_name'] = ''  # 空来源名称
        
        # 通过数据清洗管道
        cleaning_pipeline = DataCleaningPipeline()
        cleaned_item = cleaning_pipeline.process_item(item, spider=None)
        
        # 验证管道应当拒绝该item
        validation_pipeline = ValidationPipeline()
        with pytest.raises(DropItem):
            validation_pipeline.process_item(cleaned_item, spider=None)


class TestDataStorageRoundTrip:
    """
    Feature: pharmaceutical-price-discovery
    Property 2: 数据存储往返一致性
    Validates: Requirements 1.3, 2.2
    
    对于任意有效的DrugItem，保存到数据库后再查询，
    应当能够获取到相同的药品名称、价格和来源信息。
    """

    @given(
        name=drug_name_strategy,
        price=price_strategy,
        source_url=url_strategy,
        source_name=source_name_strategy
    )
    @settings(max_examples=100)
    def test_drug_and_price_round_trip(self, name, price, source_url, source_name):
        """
        Feature: pharmaceutical-price-discovery
        Property 2: 数据存储往返一致性
        Validates: Requirements 1.3, 2.2
        
        测试药品和价格记录的存储往返一致性
        """
        # 为每次测试创建新的数据库会话
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # 创建药品
            drug = Drug(name=name)
            session.add(drug)
            session.flush()  # 获取drug.id
            
            # 创建价格记录
            price_record = PriceRecord(
                drug_id=drug.id,
                price=price,
                source_url=source_url,
                source_name=source_name
            )
            session.add(price_record)
            session.commit()
            
            # 查询并验证药品
            retrieved_drug = session.query(Drug).filter_by(id=drug.id).first()
            assert retrieved_drug is not None, "药品应当能够被查询到"
            assert retrieved_drug.name == name, "药品名称应当一致"
            
            # 查询并验证价格记录
            retrieved_price = session.query(PriceRecord).filter_by(id=price_record.id).first()
            assert retrieved_price is not None, "价格记录应当能够被查询到"
            assert retrieved_price.price == price, "价格应当一致"
            assert retrieved_price.source_url == source_url, "来源URL应当一致"
            assert retrieved_price.source_name == source_name, "来源名称应当一致"
            
            # 验证关联关系
            assert retrieved_price.drug_id == retrieved_drug.id, "价格记录应当关联到正确的药品"
            
        finally:
            session.close()
            Base.metadata.drop_all(engine)
