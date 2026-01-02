"""
药师帮网站爬虫

针对 dian.ysbang.cn 的药品价格爬虫
药师帮是一个B2B医药电商平台，使用SPA架构，数据通过API接口获取

注意：
1. 此爬虫需要有效的登录Token才能访问
2. 请遵守网站的使用条款和robots.txt规则
3. 建议设置合理的请求间隔，避免对服务器造成压力

Token获取方式：
1. 手动：登录网站后从浏览器开发者工具获取
2. 自动：使用 TokenManager 工具管理Token
"""
import json
import logging
from typing import Iterator, Optional, Dict, Any
from urllib.parse import urlencode

from scrapy.http import Request, Response, JsonRequest

from scraper.items import DrugItem
from scraper.spiders.base_spider import BaseDrugSpider


class YsbangSpider(BaseDrugSpider):
    """
    药师帮爬虫
    
    通过API接口获取药品价格数据
    
    使用方式：
    scrapy crawl ysbang_spider -a token=YOUR_TOKEN -a keyword=阿莫西林
    """
    
    name = 'ysbang_spider'
    source_name = '药师帮'
    allowed_domains = ['ysbang.cn', 'dian.ysbang.cn']
    
    # API基础URL
    API_BASE_URL = 'https://dian.ysbang.cn'
    
    # 常购常搜列表接口（主要搜索接口）
    SEARCH_API = '/wholesale-drug/sales/getRegularSearchPurchaseListForPc/v5430'
    
    # 首页推荐流接口
    HOME_STREAM_API = '/wholesale-drug/sales/getHomeStreamForPc/v5430'
    
    # 自动补全接口
    AUTO_COMPLETE_API = '/wholesale-drug/sales/autoComplete/v5185'
    
    # 自定义设置
    custom_settings = {
        'DOWNLOAD_DELAY': 2,  # 请求间隔2秒
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Content-Type': 'application/json',
            'Origin': 'https://dian.ysbang.cn',
            'Referer': 'https://dian.ysbang.cn/',
        },
        # 禁用robots.txt检查（API接口通常不在robots.txt中）
        'ROBOTSTXT_OBEY': False,
    }
    
    def __init__(
        self,
        token: str = None,
        keyword: str = None,
        max_pages: int = 10,
        cookies: str = None,
        *args, **kwargs
    ):
        """
        初始化爬虫
        
        Args:
            token: 登录Token（必需）
            keyword: 搜索关键词
            max_pages: 最大爬取页数
            cookies: Cookie字符串（可选，用于增强认证）
        """
        super().__init__(*args, **kwargs)
        
        self.token = token
        self.keyword = keyword
        self.max_pages = int(max_pages)
        self.cookies = cookies or ''
        
        if not self.token:
            self.logger.warning("未提供Token，尝试从缓存加载...")
            try:
                from scraper.utils.token_manager import TokenManager
                manager = TokenManager()
                cached_token = manager._load_cached_token()
                if cached_token and manager._verify_token(cached_token):
                    self.token = cached_token
                    self.logger.info("✅ 从缓存加载Token成功")
                else:
                    self.logger.warning("请登录 https://dian.ysbang.cn 后从浏览器获取Token")
                    self.logger.warning("或使用 TokenManager.set_token_manually('your_token') 缓存Token")
            except ImportError:
                self.logger.warning("请登录 https://dian.ysbang.cn 后从浏览器获取Token")
        
        self.logger.info(f"药师帮爬虫初始化完成")
        self.logger.info(f"  - 关键词: {self.keyword or '(默认:感冒)'}")
        self.logger.info(f"  - 最大页数: {self.max_pages}")
    
    def start_requests(self):
        """
        生成初始请求
        """
        if self.keyword:
            # 搜索模式
            yield self._create_search_request(self.keyword, page=1)
        else:
            # 默认搜索常用药品
            self.logger.info("未指定关键词，使用默认搜索词'感冒'")
            yield self._create_search_request('感冒', page=1)
    
    def _create_search_request(self, keyword: str, page: int) -> Request:
        """
        创建搜索请求
        """
        url = f"{self.API_BASE_URL}{self.SEARCH_API}"
        
        body = {
            'keyword': keyword,
            'page': page,
            'pageSize': 20,
        }
        
        return JsonRequest(
            url=url,
            data=body,
            callback=self.parse_search_results,
            errback=self.errback_handler,
            headers=self._get_headers(),
            meta={
                'page': page,
                'keyword': keyword,
                'request_type': 'search'
            },
            cookies=self._get_cookies()
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """
        获取请求头
        """
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
        }
        
        if self.token:
            headers['Token'] = self.token
            headers['Authorization'] = f'Bearer {self.token}'
        
        return headers
    
    def _get_cookies(self) -> Dict[str, str]:
        """
        获取Cookie字典
        """
        cookies = {}
        if self.token:
            cookies['Token'] = self.token
        if self.cookies:
            # 解析Cookie字符串
            for item in self.cookies.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies[key.strip()] = value.strip()
        return cookies
    
    def parse_search_results(self, response: Response) -> Iterator[DrugItem]:
        """
        解析搜索结果
        """
        yield from self._parse_api_response(response)
    
    def parse_goods_list(self, response: Response) -> Iterator[DrugItem]:
        """
        解析商品列表
        """
        yield from self._parse_api_response(response)
    
    def _parse_api_response(self, response: Response) -> Iterator[DrugItem]:
        """
        解析API响应
        """
        current_page = response.meta.get('page', 1)
        request_type = response.meta.get('request_type', 'unknown')
        
        self.logger.info(f"解析第 {current_page} 页 ({request_type})")
        
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            return
        
        # 检查响应状态 - 药师帮API返回40001也可能是成功
        code = data.get('code')
        message = data.get('message', '')
        
        # 40001 + message包含"成功"表示请求成功
        if code == '40020':
            self.logger.error(f"Token无效或已过期: {message}")
            return
        
        if code not in ['0', 0, '40001'] and '成功' not in message:
            self.logger.error(f"API返回错误: code={code}, msg={message}")
            return
        
        # 提取商品列表
        result = data.get('data')
        
        if not result:
            self.logger.info(f"第 {current_page} 页无数据")
            return
        
        # 处理列表格式的响应
        items_list = []
        if isinstance(result, list):
            items_list = result
        elif isinstance(result, dict):
            items_list = (
                result.get('list') or
                result.get('items') or
                result.get('wholesaleList') or
                result.get('records') or
                []
            )
        
        if not items_list:
            self.logger.info(f"第 {current_page} 页无商品数据")
            return
        
        # 解析每个商品
        items_count = 0
        for item_data in items_list:
            item = self._parse_goods_item(item_data, response.url)
            if item:
                items_count += 1
                yield item
        
        self.logger.info(f"第 {current_page} 页解析完成，提取 {items_count} 个药品")
        
        # 处理分页
        if current_page < self.max_pages and len(items_list) >= 20:
            next_request = self._create_next_page_request(response, current_page + 1)
            if next_request:
                yield next_request
    
    def _check_response_status(self, data: Dict[str, Any]) -> bool:
        """
        检查API响应状态
        """
        # 常见的API响应格式
        code = data.get('code') or data.get('status') or data.get('errCode')
        
        if code is not None and code not in [0, 200, '0', '200', 'success']:
            msg = data.get('msg') or data.get('message') or data.get('errMsg') or '未知错误'
            self.logger.error(f"API返回错误: code={code}, msg={msg}")
            return False
        
        return True
    
    def _extract_goods_list(self, data: Dict[str, Any]) -> list:
        """
        从响应中提取商品列表
        """
        # 尝试多种可能的数据结构
        if 'data' in data:
            inner_data = data['data']
            if isinstance(inner_data, list):
                return inner_data
            elif isinstance(inner_data, dict):
                return (
                    inner_data.get('list') or
                    inner_data.get('goods') or
                    inner_data.get('items') or
                    inner_data.get('records') or
                    []
                )
        
        return data.get('list') or data.get('goods') or data.get('items') or []
    
    def _parse_goods_item(self, item_data: Dict[str, Any], source_url: str) -> Optional[DrugItem]:
        """
        解析单个商品数据
        
        药师帮API返回格式:
        {
            "elementType": 0,
            "drug": {
                "drugId": 4363,
                "drugName": "999 感冒灵颗粒 10g*9袋",
                "factory": "华润三九医药股份有限公司",
                "specification": "10g*9袋",
                "unit": "盒",
                "minprice": "13.50",
                "maxprice": "15.92",
                "approvalNumber": "国药准字Z44021940",
                ...
            }
        }
        """
        try:
            # 药师帮的数据可能嵌套在drug字段中
            goods = item_data.get('drug') or item_data
            
            # 提取药品名称
            name = (
                goods.get('drugName') or
                goods.get('goodsName') or
                goods.get('name') or
                goods.get('productName') or
                ''
            )
            
            if not name:
                return None
            
            # 提取价格 - 优先使用最低价
            price = self._extract_price(goods)
            if not price:
                self.logger.debug(f"跳过无价格商品: {name}")
                return None
            
            # 提取规格
            specification = (
                goods.get('specification') or
                goods.get('spec') or
                goods.get('goodsSpec') or
                goods.get('packSpec') or
                ''
            )
            
            # 提取单位
            unit = goods.get('unit', '')
            if unit and specification and unit not in specification:
                specification = f"{specification}/{unit}"
            
            # 提取生产厂家
            manufacturer = (
                goods.get('factory') or
                goods.get('manufacturer') or
                goods.get('produceFactory') or
                goods.get('companyName') or
                ''
            )
            
            # 提取批准文号
            approval_number = (
                goods.get('approvalNumber') or
                goods.get('approval_number') or
                goods.get('registerNo') or
                goods.get('licenseNo') or
                ''
            )
            
            # 根据批准文号判断产品类别
            category = self._determine_category(approval_number, name, manufacturer)
            
            # 构建详情页URL
            drug_id = goods.get('drugId') or goods.get('id') or goods.get('goodsId')
            detail_url = f"https://dian.ysbang.cn/#/drug/{drug_id}" if drug_id else source_url
            
            item = self.create_drug_item(
                name=name,
                price=str(price),
                source_url=detail_url,
                specification=specification,
                dosage_form='',  # 药师帮API未返回剂型
                manufacturer=manufacturer
            )
            
            # 添加批准文号和类别
            item['approval_number'] = approval_number
            item['category'] = category
            
            return item
            
        except Exception as e:
            self.logger.error(f"解析商品失败: {e}")
            return None
    
    def _determine_category(self, approval_number: str, name: str, manufacturer: str) -> str:
        """
        根据批准文号和名称判断产品类别
        
        批准文号格式：
        - 国药准字H/Z/S/J/B + 8位数字 = 药品
        - 国械注准/进 = 医疗器械
        - 卫妆准字/国妆特字 = 化妆品
        
        Returns:
            category: drug, medical_device, cosmetic, other
        """
        import re
        
        approval = (approval_number or '').upper()
        
        # 药品：国药准字
        if re.match(r'国药准字[HZSJB]\d{8}', approval):
            return 'drug'
        
        # 医疗器械：国械注准、国械注进
        if re.match(r'国械注[准进]', approval):
            return 'medical_device'
        
        # 化妆品：卫妆准字、国妆特字
        if '妆' in approval or '化妆' in approval:
            return 'cosmetic'
        
        # 根据名称和厂家判断
        cosmetic_keywords = ['珍珠霜', '珍珠膏', '护肤', '面霜', '乳液', '精华', '面膜', '化妆']
        device_keywords = ['口罩', '注射器', '体温计', '血压计', '绷带', '纱布']
        
        full_text = f"{name} {manufacturer}"
        
        for kw in cosmetic_keywords:
            if kw in full_text:
                return 'cosmetic'
        
        for kw in device_keywords:
            if kw in full_text:
                return 'medical_device'
        
        # 默认为药品（如果没有批准文号但也不是明显的非药品）
        return 'drug'
    
    def _extract_price(self, goods: Dict[str, Any]) -> Optional[float]:
        """
        提取价格 - 优先使用最低价
        """
        # 药师帮返回minprice和maxprice
        price_fields = [
            'minprice', 'minPrice', 'price', 'salePrice', 'sellPrice', 
            'retailPrice', 'goodsPrice', 'unitPrice', 'showPrice'
        ]
        
        for field in price_fields:
            price = goods.get(field)
            if price is not None:
                try:
                    # 处理价格字符串
                    if isinstance(price, str):
                        price = price.replace('¥', '').replace('￥', '').replace('元', '').strip()
                    return float(price)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _has_more_pages(self, data: Dict[str, Any], current_page: int) -> bool:
        """
        检查是否有更多页面
        """
        # 尝试从响应中获取分页信息
        inner_data = data.get('data', data)
        
        if isinstance(inner_data, dict):
            total_pages = inner_data.get('totalPages') or inner_data.get('pages')
            if total_pages:
                return current_page < int(total_pages)
            
            total = inner_data.get('total') or inner_data.get('totalCount')
            page_size = inner_data.get('pageSize') or inner_data.get('size') or 20
            if total:
                return current_page * page_size < int(total)
            
            # 检查是否有下一页标记
            has_next = inner_data.get('hasNext') or inner_data.get('hasMore')
            if has_next is not None:
                return bool(has_next)
        
        # 默认继续爬取
        return True
    
    def _create_next_page_request(self, response: Response, next_page: int) -> Optional[Request]:
        """
        创建下一页请求
        """
        keyword = response.meta.get('keyword', '感冒')
        return self._create_search_request(keyword, next_page)
    
    def parse(self, response: Response) -> Iterator[DrugItem]:
        """
        默认解析方法（兼容基类）
        """
        yield from self._parse_api_response(response)
