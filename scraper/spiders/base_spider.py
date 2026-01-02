"""
基础爬虫类
提供药品价格爬虫的基础功能和通用方法
"""
import logging
from abc import abstractmethod
from typing import Iterator, Optional

import scrapy
from scrapy.http import Response

from scraper.items import DrugItem


class BaseDrugSpider(scrapy.Spider):
    """
    药品爬虫基类
    
    所有药品网站爬虫应继承此类并实现parse方法
    提供通用的错误处理和数据提取辅助方法
    """
    
    # 子类必须定义的属性
    name: str = 'base_drug_spider'
    allowed_domains: list = []
    start_urls: list = []
    source_name: str = ''  # 来源网站名称
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.setLevel(logging.INFO)
    
    @abstractmethod
    def parse(self, response: Response) -> Iterator[DrugItem]:
        """
        解析页面，提取药品信息
        
        子类必须实现此方法
        
        Args:
            response: Scrapy响应对象
            
        Yields:
            DrugItem: 药品数据项
        """
        raise NotImplementedError("子类必须实现parse方法")
    
    def create_drug_item(
        self,
        name: str,
        price: str,
        source_url: str,
        specification: str = '',
        dosage_form: str = '',
        manufacturer: str = ''
    ) -> DrugItem:
        """
        创建药品数据项的辅助方法
        
        Args:
            name: 药品名称
            price: 价格字符串
            source_url: 来源URL
            specification: 规格
            dosage_form: 剂型
            manufacturer: 生产厂家
            
        Returns:
            DrugItem: 填充好的药品数据项
        """
        item = DrugItem()
        item['name'] = name.strip() if name else ''
        item['price'] = price.strip() if price else ''
        item['source_url'] = source_url
        item['source_name'] = self.source_name
        item['specification'] = specification.strip() if specification else ''
        item['dosage_form'] = dosage_form.strip() if dosage_form else ''
        item['manufacturer'] = manufacturer.strip() if manufacturer else ''
        return item
    
    def extract_text(self, response: Response, selector: str, default: str = '') -> str:
        """
        安全地从响应中提取文本
        
        Args:
            response: Scrapy响应对象
            selector: CSS选择器
            default: 默认值
            
        Returns:
            str: 提取的文本或默认值
        """
        try:
            text = response.css(selector).get()
            return text.strip() if text else default
        except Exception as e:
            self.logger.warning(f"提取文本失败 [{selector}]: {e}")
            return default
    
    def extract_text_xpath(self, response: Response, xpath: str, default: str = '') -> str:
        """
        使用XPath安全地从响应中提取文本
        
        Args:
            response: Scrapy响应对象
            xpath: XPath表达式
            default: 默认值
            
        Returns:
            str: 提取的文本或默认值
        """
        try:
            text = response.xpath(xpath).get()
            return text.strip() if text else default
        except Exception as e:
            self.logger.warning(f"提取文本失败 [{xpath}]: {e}")
            return default
    
    def errback_handler(self, failure):
        """
        统一的错误处理回调
        
        Args:
            failure: Twisted Failure对象
        """
        request = failure.request
        self.logger.error(f"请求失败: {request.url}")
        self.logger.error(f"错误类型: {failure.type}")
        self.logger.error(f"错误信息: {failure.value}")
