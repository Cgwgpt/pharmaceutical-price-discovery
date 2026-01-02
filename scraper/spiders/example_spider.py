"""
通用HTML药品网站爬虫模板

这是一个通用的HTML页面爬虫模板，展示如何继承BaseDrugSpider实现药品价格爬取。
适用于传统的服务端渲染网站（非SPA）。

对于SPA网站（如药师帮），请参考 ysbang_spider.py 使用API接口方式。

使用时需要根据目标网站的HTML结构调整选择器。
"""
import logging
from typing import Iterator, Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

from scrapy.http import Response, Request

from scraper.items import DrugItem
from scraper.spiders.base_spider import BaseDrugSpider


class ExampleDrugSpider(BaseDrugSpider):
    """
    示例药品爬虫
    
    演示如何实现一个完整的药品价格爬虫，包括：
    - 页面解析逻辑
    - 分页处理
    - 错误处理和重试
    
    HTML结构假设：
    - 药品列表在 .drug-list .drug-item 中
    - 药品名称在 .drug-name 中
    - 价格在 .drug-price 中
    - 规格在 .drug-spec 中
    - 分页链接在 .pagination .next-page 中
    """
    
    name = 'example_drug_spider'
    source_name = '示例药品网'
    
    # 自定义设置
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
    }
    
    def __init__(self, start_url: str = None, *args, **kwargs):
        """
        初始化爬虫
        
        Args:
            start_url: 可选的起始URL，用于命令行指定
        """
        super().__init__(*args, **kwargs)
        
        # 支持通过命令行参数指定起始URL
        if start_url:
            self.start_urls = [start_url]
            # 从URL中提取域名
            parsed = urlparse(start_url)
            self.allowed_domains = [parsed.netloc]
        else:
            # 默认配置（示例URL，实际使用时需要替换）
            self.start_urls = ['http://example-pharmacy.com/drugs']
            self.allowed_domains = ['example-pharmacy.com']
        
        self.logger.info(f"爬虫初始化完成，起始URL: {self.start_urls}")
    
    def start_requests(self):
        """
        生成初始请求
        
        为每个起始URL创建请求，并设置错误回调
        """
        for url in self.start_urls:
            yield Request(
                url=url,
                callback=self.parse,
                errback=self.errback_handler,
                meta={'page': 1}
            )
    
    def parse(self, response: Response) -> Iterator[DrugItem]:
        """
        解析药品列表页面
        
        Args:
            response: Scrapy响应对象
            
        Yields:
            DrugItem: 药品数据项
            Request: 下一页请求
        """
        current_page = response.meta.get('page', 1)
        self.logger.info(f"正在解析第 {current_page} 页: {response.url}")
        
        # 检查响应状态
        if response.status != 200:
            self.logger.warning(f"页面返回非200状态码: {response.status}")
            return
        
        # 解析药品列表
        drug_items = response.css('.drug-list .drug-item')
        
        if not drug_items:
            # 尝试备用选择器
            drug_items = response.css('.product-list .product-item')
        
        if not drug_items:
            self.logger.warning(f"未找到药品列表，页面可能结构变化: {response.url}")
            return
        
        items_count = 0
        for drug_element in drug_items:
            item = self._parse_drug_item(drug_element, response)
            if item:
                items_count += 1
                yield item
        
        self.logger.info(f"第 {current_page} 页解析完成，提取 {items_count} 个药品")
        
        # 处理分页
        next_page_request = self._get_next_page_request(response, current_page)
        if next_page_request:
            yield next_page_request
    
    def _parse_drug_item(self, element, response: Response) -> Optional[DrugItem]:
        """
        解析单个药品元素
        
        Args:
            element: 药品HTML元素
            response: 响应对象
            
        Returns:
            DrugItem或None（解析失败时）
        """
        try:
            # 提取药品名称
            name = element.css('.drug-name::text').get()
            if not name:
                name = element.css('.product-name::text').get()
            
            if not name:
                self.logger.debug("跳过无名称的药品项")
                return None
            
            # 提取价格
            price = element.css('.drug-price::text').get()
            if not price:
                price = element.css('.price::text').get()
            
            if not price:
                self.logger.debug(f"跳过无价格的药品: {name}")
                return None
            
            # 提取规格
            specification = element.css('.drug-spec::text').get()
            if not specification:
                specification = element.css('.specification::text').get()
            
            # 提取剂型
            dosage_form = element.css('.drug-form::text').get()
            if not dosage_form:
                dosage_form = element.css('.dosage-form::text').get()
            
            # 提取生产厂家
            manufacturer = element.css('.drug-manufacturer::text').get()
            if not manufacturer:
                manufacturer = element.css('.manufacturer::text').get()
            
            # 获取详情页URL（如果有）
            detail_url = element.css('a::attr(href)').get()
            source_url = urljoin(response.url, detail_url) if detail_url else response.url
            
            # 创建药品数据项
            return self.create_drug_item(
                name=name,
                price=price,
                source_url=source_url,
                specification=specification or '',
                dosage_form=dosage_form or '',
                manufacturer=manufacturer or ''
            )
            
        except Exception as e:
            self.logger.error(f"解析药品项失败: {e}")
            return None
    
    def _get_next_page_request(self, response: Response, current_page: int) -> Optional[Request]:
        """
        获取下一页请求
        
        支持多种分页方式：
        1. 下一页链接
        2. 页码参数
        
        Args:
            response: 当前响应
            current_page: 当前页码
            
        Returns:
            下一页Request或None
        """
        # 方式1: 查找下一页链接
        next_page_url = response.css('.pagination .next-page::attr(href)').get()
        if not next_page_url:
            next_page_url = response.css('.pager .next a::attr(href)').get()
        if not next_page_url:
            next_page_url = response.css('a.next::attr(href)').get()
        
        if next_page_url:
            absolute_url = urljoin(response.url, next_page_url)
            self.logger.info(f"发现下一页链接: {absolute_url}")
            return Request(
                url=absolute_url,
                callback=self.parse,
                errback=self.errback_handler,
                meta={'page': current_page + 1}
            )
        
        # 方式2: 检查是否有更多页面（通过页码）
        # 查找最大页码
        page_numbers = response.css('.pagination .page-number::text').getall()
        if page_numbers:
            try:
                max_page = max(int(p.strip()) for p in page_numbers if p.strip().isdigit())
                if current_page < max_page:
                    # 构建下一页URL
                    next_url = self._build_page_url(response.url, current_page + 1)
                    self.logger.info(f"构建下一页URL: {next_url}")
                    return Request(
                        url=next_url,
                        callback=self.parse,
                        errback=self.errback_handler,
                        meta={'page': current_page + 1}
                    )
            except ValueError:
                pass
        
        self.logger.info(f"已到达最后一页（第 {current_page} 页）")
        return None
    
    def _build_page_url(self, base_url: str, page: int) -> str:
        """
        构建分页URL
        
        Args:
            base_url: 基础URL
            page: 页码
            
        Returns:
            带页码参数的URL
        """
        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query)
        query_params['page'] = [str(page)]
        
        new_query = urlencode(query_params, doseq=True)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
    
    def errback_handler(self, failure):
        """
        错误处理回调
        
        记录详细的错误信息，便于调试和监控
        
        Args:
            failure: Twisted Failure对象
        """
        request = failure.request
        
        # 记录错误详情
        self.logger.error(f"请求失败: {request.url}")
        self.logger.error(f"错误类型: {failure.type.__name__}")
        self.logger.error(f"错误信息: {failure.value}")
        
        # 记录请求元数据
        page = request.meta.get('page', 'unknown')
        self.logger.error(f"失败页码: {page}")
        
        # 统计错误（可用于监控）
        self.crawler.stats.inc_value('error_count')
        self.crawler.stats.inc_value(f'error_count/{failure.type.__name__}')
