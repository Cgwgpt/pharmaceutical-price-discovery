"""
Scrapy数据项定义
定义DrugItem用于存储爬取的药品信息
"""
import scrapy


class DrugItem(scrapy.Item):
    """
    药品数据项
    
    用于在爬虫和管道之间传递药品信息
    """
    # 药品名称
    name = scrapy.Field()
    
    # 规格（如：10mg*24片）
    specification = scrapy.Field()
    
    # 价格（字符串格式，需在管道中清洗）
    price = scrapy.Field()
    
    # 来源URL
    source_url = scrapy.Field()
    
    # 来源网站名称
    source_name = scrapy.Field()
    
    # 剂型（可选）
    dosage_form = scrapy.Field()
    
    # 生产厂家（可选）
    manufacturer = scrapy.Field()
    
    # 批准文号（如：国药准字Z35020243）
    approval_number = scrapy.Field()
    
    # 产品类别（drug=药品, medical_device=医疗器械, cosmetic=化妆品, other=其他）
    category = scrapy.Field()
