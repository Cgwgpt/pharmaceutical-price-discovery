"""
Playwright 浏览器自动化爬虫

用于获取药师帮药品详情页中每个供应商的具体价格

核心功能:
1. 通过浏览器自动化访问药师帮网站
2. 拦截 API 请求获取供应商价格数据
3. 支持搜索结果页和药品详情页两种模式
"""
import asyncio
import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class YSBangPlaywrightCrawler:
    """
    药师帮 Playwright 爬虫
    
    通过浏览器自动化 + API 拦截获取药品详情页中每个供应商的具体价格
    
    工作原理:
    1. 使用 Playwright 打开浏览器，设置 Token Cookie
    2. 拦截页面发出的 API 请求，直接获取 JSON 数据
    3. 从 API 响应中提取供应商价格信息
    """
    
    def __init__(self, token: str = None, headless: bool = True):
        """
        初始化爬虫
        
        Args:
            token: 登录Token（可选，如果不提供则从缓存读取）
            headless: 是否无头模式运行
        """
        self.token = token or self._get_cached_token()
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self._api_responses = []  # 存储拦截到的 API 响应
    
    def _get_cached_token(self) -> str:
        """获取缓存的Token"""
        import os
        cache_file = '.token_cache.json'
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
                return cache.get('token', '')
        except:
            pass
        return ''
    
    async def _init_browser(self):
        """初始化浏览器"""
        from playwright.async_api import async_playwright
        
        self.playwright = await async_playwright().start()
        self._api_responses = []  # 重置 API 响应列表
        
        # 尝试使用系统 Chrome 或已安装的 Chromium
        try:
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                channel='chrome'  # 使用系统安装的 Chrome
            )
        except Exception as e:
            logger.warning(f"无法使用系统 Chrome: {e}, 尝试使用 Playwright Chromium")
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
        
        # 创建上下文，设置Cookie
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # 设置Token Cookie
        if self.token:
            await self.context.add_cookies([{
                'name': 'Token',
                'value': self.token,
                'domain': 'dian.ysbang.cn',
                'path': '/'
            }])
        
        self.page = await self.context.new_page()
        
        # 设置 API 请求拦截
        await self._setup_api_interception()
    
    async def _setup_api_interception(self):
        """设置 API 请求拦截，捕获供应商价格数据"""
        
        async def handle_response(response):
            """处理响应，提取 API 数据"""
            url = response.url
            
            # 只关注药师帮的 API 请求
            if 'dian.ysbang.cn' not in url:
                return
            
            # 关注的 API 端点
            api_patterns = [
                'getWholesaleListForPc',      # 供应商列表（包含价格）
                'facetWholesaleList',          # 供应商聚合列表
                'getRegularSearchPurchaseList', # 搜索结果
                'getHotWholesalesForProvider',  # 供应商热销商品
                'getDrugDetail',               # 药品详情
            ]
            
            if any(pattern in url for pattern in api_patterns):
                try:
                    body = await response.body()
                    data = json.loads(body.decode('utf-8'))
                    self._api_responses.append({
                        'url': url,
                        'data': data,
                        'timestamp': datetime.now().isoformat()
                    })
                    logger.debug(f"拦截到 API: {url[:80]}...")
                except Exception as e:
                    logger.debug(f"解析 API 响应失败: {e}")
        
        self.page.on('response', handle_response)
    
    async def _close_browser(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def get_drug_provider_prices(
        self,
        keyword: str,
        drug_id: int = None,
        max_providers: int = 50
    ) -> Dict[str, Any]:
        """
        获取药品的所有供应商价格
        
        通过两种方式获取数据:
        1. 拦截 API 请求，直接获取 JSON 数据（更准确）
        2. 从页面 DOM 提取数据（作为备选）
        
        关键发现:
        - URL带 drugId 参数时，会显示该药品的所有供应商（如23个供应商）
        - URL不带 drugId 时，显示所有相关商品（可能包含不同规格）
        - 页面会调用 getWholesaleListForPc API 获取供应商列表
        
        Args:
            keyword: 药品关键词
            drug_id: 药品ID（可选，但强烈建议提供以获取准确结果）
            max_providers: 最大供应商数量
            
        Returns:
            包含供应商价格列表的字典
        """
        results = {
            'keyword': keyword,
            'drug_id': drug_id,
            'providers': [],
            'success': False,
            'error': None
        }
        
        try:
            await self._init_browser()
            
            # 构建搜索URL
            # 使用 drugId 参数可以显示该药品的所有供应商
            if drug_id:
                url = f'https://dian.ysbang.cn/#/indexContent?drugId={drug_id}&searchkey={keyword}'
            else:
                url = f'https://dian.ysbang.cn/#/indexContent?searchkey={keyword}'
            
            logger.info(f"访问页面: {url}")
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            
            # 等待商品卡片加载
            try:
                await self.page.wait_for_selector('.all-goods-wrapper', timeout=15000)
            except:
                # 可能需要登录或页面结构不同
                results['error'] = '页面加载超时，可能需要登录'
                return results
            
            await asyncio.sleep(2)  # 等待数据完全加载
            
            # 滚动页面加载更多供应商
            await self._scroll_to_load_all(max_providers)
            
            # 等待更多 API 响应
            await asyncio.sleep(1)
            
            # 优先从拦截的 API 响应中提取数据
            provider_prices = self._extract_prices_from_api_responses(keyword)
            
            # 如果 API 数据不足，从页面 DOM 提取
            if len(provider_prices) < 5:
                logger.info("API 数据不足，从页面 DOM 提取...")
                dom_prices = await self._extract_all_provider_prices(keyword)
                # 合并去重
                existing_providers = {p.get('provider_name', '') for p in provider_prices}
                for p in dom_prices:
                    if p.get('provider_name', '') not in existing_providers:
                        provider_prices.append(p)
            
            if not provider_prices:
                results['error'] = '未找到供应商价格'
                return results
            
            results['providers'] = provider_prices[:max_providers]
            results['total_found'] = len(provider_prices)
            results['drug_name'] = keyword
            results['success'] = True
            
            logger.info(f"找到 {len(provider_prices)} 个供应商价格")
            
        except Exception as e:
            logger.error(f"爬取失败: {e}")
            results['error'] = str(e)
        finally:
            await self._close_browser()
        
        return results
    
    def _extract_prices_from_api_responses(self, keyword: str) -> List[Dict[str, Any]]:
        """
        从拦截的 API 响应中提取供应商价格
        
        Args:
            keyword: 搜索关键词（用于过滤）
            
        Returns:
            供应商价格列表
        """
        provider_prices = []
        seen_providers = set()  # 用于去重
        
        for response in self._api_responses:
            url = response.get('url', '')
            data = response.get('data', {})
            
            # 处理 getWholesaleListForPc 响应（供应商列表）
            if 'getWholesaleListForPc' in url:
                items = self._extract_items_from_response(data)
                for item in items:
                    provider_info = self._parse_wholesale_item(item)
                    if provider_info and provider_info.get('provider_name') not in seen_providers:
                        seen_providers.add(provider_info.get('provider_name'))
                        provider_prices.append(provider_info)
            
            # 处理 getRegularSearchPurchaseList 响应（搜索结果）
            elif 'getRegularSearchPurchaseList' in url:
                items = self._extract_items_from_response(data)
                for item in items:
                    # 这个 API 返回的是聚合数据，包含 drug 字段
                    drug = item.get('drug', item)
                    provider_info = self._parse_drug_item(drug)
                    if provider_info:
                        provider_prices.append(provider_info)
            
            # 处理 facetWholesaleList 响应
            elif 'facetWholesaleList' in url:
                # 这个 API 返回供应商聚合信息
                result = data.get('data', {})
                if isinstance(result, dict):
                    wholesales = result.get('wholesales', [])
                    for item in wholesales:
                        provider_info = self._parse_wholesale_item(item)
                        if provider_info and provider_info.get('provider_name') not in seen_providers:
                            seen_providers.add(provider_info.get('provider_name'))
                            provider_prices.append(provider_info)
        
        logger.info(f"从 API 响应中提取了 {len(provider_prices)} 个供应商价格")
        return provider_prices
    
    def _extract_items_from_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从 API 响应中提取商品列表"""
        result = data.get('data', data)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            return (
                result.get('list') or
                result.get('wholesales') or
                result.get('items') or
                result.get('records') or
                []
            )
        return []
    
    def _parse_wholesale_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析供应商商品数据
        
        供应商列表 API 返回格式:
        {
            "wholesaleid": 123456,
            "drugname": "药品名称",
            "price": "12.50",
            "abbreviation": "供应商简称",
            "providerId": 789,
            "specification": "规格",
            "manufacturer": "厂家"
        }
        """
        try:
            drug_name = item.get('drugname', item.get('drugName', ''))
            price_str = item.get('price', item.get('showPrice', ''))
            provider_name = item.get('abbreviation', item.get('providerName', ''))
            
            if not drug_name or not price_str:
                return None
            
            # 清理价格
            price_clean = re.sub(r'[^\d.]', '', str(price_str))
            try:
                price = float(price_clean) if price_clean else 0
            except:
                price = 0
            
            if price <= 0:
                return None
            
            return {
                'drug_name': drug_name.strip(),
                'provider_name': provider_name.strip(),
                'provider_id': item.get('providerId', item.get('provider_id', '')),
                'price': price,
                'price_raw': f'¥{price:.2f}',
                'manufacturer': item.get('manufacturer', item.get('factory', '')).strip(),
                'specification': item.get('specification', item.get('spec', '')).strip(),
                'wholesale_id': item.get('wholesaleid', item.get('wholesaleId', '')),
                'source': 'api'
            }
        except Exception as e:
            logger.debug(f"解析供应商商品失败: {e}")
            return None
    
    def _parse_drug_item(self, drug: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析药品聚合数据
        
        搜索 API 返回格式:
        {
            "drugId": 123,
            "drugName": "药品名称",
            "minprice": "10.00",
            "maxprice": "15.00",
            "wholesaleNum": 23,
            "factory": "厂家",
            "specification": "规格"
        }
        """
        try:
            drug_name = drug.get('drugName', drug.get('drugname', ''))
            min_price = drug.get('minprice', drug.get('price', ''))
            
            if not drug_name or not min_price:
                return None
            
            price_clean = re.sub(r'[^\d.]', '', str(min_price))
            try:
                price = float(price_clean) if price_clean else 0
            except:
                price = 0
            
            if price <= 0:
                return None
            
            wholesale_num = drug.get('wholesaleNum', 1)
            
            return {
                'drug_name': drug_name.strip(),
                'provider_name': f'聚合({wholesale_num}家)',
                'drug_id': drug.get('drugId', drug.get('drug_id', '')),
                'price': price,
                'price_raw': f'¥{price:.2f}',
                'max_price': drug.get('maxprice', ''),
                'manufacturer': drug.get('factory', drug.get('manufacturer', '')).strip(),
                'specification': drug.get('specification', '').strip(),
                'wholesale_num': wholesale_num,
                'source': 'api_aggregated'
            }
        except Exception as e:
            logger.debug(f"解析药品数据失败: {e}")
            return None
    
    async def _scroll_to_load_all(self, max_items: int = 50):
        """滚动页面加载更多商品"""
        last_count = 0
        scroll_attempts = 0
        max_scroll_attempts = 10
        
        while scroll_attempts < max_scroll_attempts:
            # 获取当前商品数量
            cards = await self.page.query_selector_all('.all-goods-wrapper')
            current_count = len(cards)
            
            if current_count >= max_items:
                break
            
            if current_count == last_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_count = current_count
            
            # 滚动到页面底部
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)
        
        logger.info(f"滚动加载完成，共 {last_count} 个商品卡片")
    
    async def _extract_all_provider_prices(self, keyword: str) -> List[Dict[str, Any]]:
        """
        从页面提取所有供应商价格
        
        使用正确的选择器:
        - 卡片: .all-goods-wrapper
        - 名称: .goods-name
        - 价格: .goods-price-all .font-semibold (第二个元素是价格数字)
        - 供应商: .goods-footer-info
        - 厂家: .goods-manufacturer
        """
        provider_prices = []
        
        try:
            cards = await self.page.query_selector_all('.all-goods-wrapper')
            logger.info(f"找到 {len(cards)} 个商品卡片")
            
            for card in cards:
                try:
                    # 提取药品名称
                    name_el = await card.query_selector('.goods-name')
                    name = await name_el.inner_text() if name_el else ''
                    
                    # 提取价格 - 使用正确的选择器
                    price_spans = await card.query_selector_all('.goods-price-all .font-semibold')
                    price_text = ''
                    if len(price_spans) >= 2:
                        # 第二个元素是价格数字
                        price_text = await price_spans[1].inner_text()
                    elif price_spans:
                        price_text = await price_spans[0].inner_text()
                    
                    # 提取供应商名称
                    provider_el = await card.query_selector('.goods-footer-info')
                    provider_name = await provider_el.inner_text() if provider_el else ''
                    
                    # 提取厂家
                    manufacturer_el = await card.query_selector('.goods-manufacturer')
                    manufacturer = await manufacturer_el.inner_text() if manufacturer_el else ''
                    
                    # 提取规格（通常在名称后面或单独的元素中）
                    spec_el = await card.query_selector('.goods-spec, .specification')
                    spec = await spec_el.inner_text() if spec_el else ''
                    
                    # 清理价格
                    price_clean = re.sub(r'[^\d.]', '', price_text)
                    try:
                        price_float = float(price_clean) if price_clean else 0
                    except:
                        price_float = 0
                    
                    if price_float > 0:
                        provider_prices.append({
                            'drug_name': name.strip(),
                            'provider_name': provider_name.strip(),
                            'price': price_float,
                            'price_raw': f'¥{price_text.strip()}',
                            'manufacturer': manufacturer.strip(),
                            'specification': spec.strip()
                        })
                        
                except Exception as e:
                    logger.debug(f"提取商品信息失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"提取供应商价格失败: {e}")
        
        return provider_prices
    
    async def _extract_drug_items(self) -> List[Dict[str, Any]]:
        """
        从页面提取药品列表
        
        使用正确的选择器:
        - 卡片: .all-goods-wrapper
        - 名称: .goods-name
        - 价格: .goods-price-all .font-semibold (第二个元素是价格数字)
        - 供应商: .goods-footer-info
        - 厂家: .goods-manufacturer
        """
        items = []
        
        try:
            # 获取所有商品卡片
            cards = await self.page.query_selector_all('.all-goods-wrapper')
            
            for card in cards[:30]:  # 处理前30个
                try:
                    # 提取药品名称
                    name_el = await card.query_selector('.goods-name')
                    name = await name_el.inner_text() if name_el else ''
                    
                    # 提取价格 - 第二个 .font-semibold 是价格数字
                    price_spans = await card.query_selector_all('.goods-price-all .font-semibold')
                    price = ''
                    if len(price_spans) >= 2:
                        price = await price_spans[1].inner_text()
                    elif price_spans:
                        price = await price_spans[0].inner_text()
                    
                    # 提取供应商名称
                    footer_el = await card.query_selector('.goods-footer-info')
                    provider = await footer_el.inner_text() if footer_el else ''
                    
                    # 提取厂家
                    manufacturer_el = await card.query_selector('.goods-manufacturer')
                    manufacturer = await manufacturer_el.inner_text() if manufacturer_el else ''
                    
                    if name:
                        items.append({
                            'name': name.strip(),
                            'price': price.strip(),
                            'provider': provider.strip(),
                            'manufacturer': manufacturer.strip(),
                            'element': card
                        })
                except Exception as e:
                    logger.debug(f"提取商品信息失败: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"提取商品列表失败: {e}")
        
        return items
    
    async def _get_provider_prices_from_detail(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从详情页获取供应商价格（已废弃，保留兼容性）
        
        新实现直接从搜索结果页提取，无需点击进入详情页
        """
        # 直接返回空列表，使用 _extract_all_provider_prices 代替
        return []
    
    async def _scroll_and_extract_prices(self, provider_prices: List[Dict[str, Any]]):
        """滚动页面并提取价格（已废弃，保留兼容性）"""
        # 使用 _scroll_to_load_all 和 _extract_all_provider_prices 代替
        pass

    
    async def search_and_get_all_prices(
        self,
        keyword: str,
        max_items: int = 10
    ) -> Dict[str, Any]:
        """
        搜索药品并获取所有供应商价格
        
        通过 API 拦截 + DOM 提取双重方式获取数据
        
        Args:
            keyword: 搜索关键词
            max_items: 最大处理商品数量
            
        Returns:
            包含所有商品供应商价格的字典
        """
        results = {
            'keyword': keyword,
            'items': [],
            'success': False,
            'error': None
        }
        
        try:
            await self._init_browser()
            
            # 访问搜索页面
            url = f'https://dian.ysbang.cn/#/indexContent?searchkey={keyword}'
            logger.info(f"访问搜索页面: {url}")
            
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            await self.page.wait_for_selector('.all-goods-wrapper', timeout=15000)
            await asyncio.sleep(2)
            
            # 滚动加载更多
            await self._scroll_to_load_all(max_items)
            
            # 等待更多 API 响应
            await asyncio.sleep(1)
            
            # 从 API 响应中提取数据
            all_prices = self._extract_prices_from_api_responses(keyword)
            
            # 如果 API 数据不足，从 DOM 提取
            if len(all_prices) < 5:
                logger.info("API 数据不足，从页面 DOM 提取...")
                dom_prices = await self._extract_all_provider_prices(keyword)
                existing_providers = {p.get('provider_name', '') for p in all_prices}
                for p in dom_prices:
                    if p.get('provider_name', '') not in existing_providers:
                        all_prices.append(p)
            
            # 按药品名称分组
            drug_groups = {}
            for item in all_prices:
                drug_name = item.get('drug_name', '')
                if drug_name not in drug_groups:
                    drug_groups[drug_name] = {
                        'name': drug_name,
                        'manufacturer': item.get('manufacturer', ''),
                        'specification': item.get('specification', ''),
                        'provider_prices': []
                    }
                drug_groups[drug_name]['provider_prices'].append({
                    'provider_name': item.get('provider_name'),
                    'provider_id': item.get('provider_id'),
                    'price': item.get('price'),
                    'price_raw': item.get('price_raw'),
                    'wholesale_id': item.get('wholesale_id'),
                    'source': item.get('source', 'unknown')
                })
            
            results['items'] = list(drug_groups.values())[:max_items]
            results['total_providers'] = len(all_prices)
            results['success'] = True
            
            logger.info(f"找到 {len(drug_groups)} 种药品，共 {len(all_prices)} 个供应商价格")
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            results['error'] = str(e)
        finally:
            await self._close_browser()
        
        return results
    
    async def _extract_provider_prices_from_page(self) -> List[Dict[str, Any]]:
        """从当前页面提取供应商价格（已废弃，保留兼容性）"""
        # 使用 _extract_all_provider_prices 代替
        return await self._extract_all_provider_prices('')
    
    async def get_drug_detail_prices(
        self,
        keyword: str,
        drug_id: int = None,
        max_providers: int = 100
    ) -> Dict[str, Any]:
        """
        获取单个药品的所有供应商详细价格
        
        通过访问药品详情页，获取该药品在所有供应商的价格
        这个方法会:
        1. 如果提供 drug_id，直接访问详情页
        2. 如果没有 drug_id，在搜索页面直接提取数据（不点击进入详情页）
        3. 拦截 getWholesaleListForPc API 获取所有供应商价格
        
        Args:
            keyword: 药品关键词
            drug_id: 药品ID（如果提供，直接访问详情页）
            max_providers: 最大供应商数量
            
        Returns:
            包含所有供应商价格的字典
        """
        results = {
            'keyword': keyword,
            'drug_id': drug_id,
            'drug_name': '',
            'providers': [],
            'success': False,
            'error': None
        }
        
        try:
            await self._init_browser()
            
            if drug_id:
                # 直接访问药品详情页
                url = f'https://dian.ysbang.cn/#/drug/{drug_id}'
                logger.info(f"访问药品详情页: {url}")
                await self.page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
            else:
                # 在搜索页面直接提取数据，不点击进入详情页
                url = f'https://dian.ysbang.cn/#/indexContent?searchkey={keyword}'
                logger.info(f"访问搜索页面: {url}")
                await self.page.goto(url, wait_until='networkidle', timeout=30000)
                
                # 等待商品卡片加载
                try:
                    await self.page.wait_for_selector('.all-goods-wrapper', timeout=15000)
                except:
                    results['error'] = '页面加载超时，可能需要登录'
                    return results
                
                await asyncio.sleep(2)
            
            # 获取药品名称
            try:
                name_el = await self.page.query_selector('.drug-name, .goods-name, h1')
                if name_el:
                    results['drug_name'] = await name_el.inner_text()
            except:
                results['drug_name'] = keyword
            
            # 滚动页面加载更多供应商
            await self._scroll_to_load_all(max_providers)
            
            # 等待 API 响应
            await asyncio.sleep(1)
            
            # 从 API 响应中提取供应商价格
            provider_prices = self._extract_prices_from_api_responses(keyword)
            
            # 如果 API 数据不足，从 DOM 提取
            if len(provider_prices) < 5:
                dom_prices = await self._extract_all_provider_prices(keyword)
                existing = {p.get('provider_name', '') for p in provider_prices}
                for p in dom_prices:
                    if p.get('provider_name', '') not in existing:
                        provider_prices.append(p)
            
            # 按价格排序
            provider_prices.sort(key=lambda x: x.get('price', 0))
            
            results['providers'] = provider_prices[:max_providers]
            results['total_found'] = len(provider_prices)
            results['success'] = True
            
            # 计算价格统计
            if provider_prices:
                prices = [p.get('price', 0) for p in provider_prices if p.get('price', 0) > 0]
                if prices:
                    results['price_stats'] = {
                        'min': min(prices),
                        'max': max(prices),
                        'avg': sum(prices) / len(prices),
                        'count': len(prices)
                    }
            
            logger.info(f"找到 {len(provider_prices)} 个供应商价格")
            
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            results['error'] = str(e)
        finally:
            await self._close_browser()
        
        return results


def crawl_drug_prices_sync(keyword: str, drug_id: int = None, token: str = None, headless: bool = True) -> Dict[str, Any]:
    """
    同步方式爬取药品价格
    
    Args:
        keyword: 药品关键词
        drug_id: 药品ID（强烈建议提供，可获取该药品的所有供应商价格）
        token: 登录Token
        headless: 是否无头模式
        
    Returns:
        爬取结果
    """
    crawler = YSBangPlaywrightCrawler(token=token, headless=headless)
    return asyncio.run(crawler.get_drug_provider_prices(keyword, drug_id=drug_id))


def search_and_crawl_sync(keyword: str, token: str = None, max_items: int = 10, headless: bool = True) -> Dict[str, Any]:
    """
    同步方式搜索并爬取所有供应商价格
    
    Args:
        keyword: 搜索关键词
        token: 登录Token
        max_items: 最大处理商品数量
        headless: 是否无头模式
        
    Returns:
        爬取结果
    """
    crawler = YSBangPlaywrightCrawler(token=token, headless=headless)
    return asyncio.run(crawler.search_and_get_all_prices(keyword, max_items))


def crawl_drug_detail_sync(keyword: str, drug_id: int = None, token: str = None, max_providers: int = 100, headless: bool = True) -> Dict[str, Any]:
    """
    同步方式获取单个药品的所有供应商价格
    
    这是获取供应商具体价格的推荐方法
    
    Args:
        keyword: 药品关键词
        drug_id: 药品ID（可选）
        token: 登录Token
        max_providers: 最大供应商数量
        headless: 是否无头模式
        
    Returns:
        爬取结果，包含:
        - drug_name: 药品名称
        - providers: 供应商价格列表（按价格排序）
        - price_stats: 价格统计（最低、最高、平均）
    """
    crawler = YSBangPlaywrightCrawler(token=token, headless=headless)
    return asyncio.run(crawler.get_drug_detail_prices(keyword, drug_id=drug_id, max_providers=max_providers))


if __name__ == '__main__':
    # 测试
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    keyword = sys.argv[1] if len(sys.argv) > 1 else '片仔癀'
    drug_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    print(f"\n{'='*60}")
    print(f"🎭 Playwright 药品价格采集")
    print(f"{'='*60}")
    print(f"搜索关键词: {keyword}")
    if drug_id:
        print(f"药品ID: {drug_id}")
    print(f"{'='*60}\n")
    
    # 使用 get_drug_detail_prices 获取单个药品的所有供应商价格
    result = crawl_drug_detail_sync(keyword, drug_id=drug_id, headless=True)
    
    print(f"\n{'='*60}")
    print(f"📊 采集结果")
    print(f"{'='*60}")
    print(f"成功: {'✅' if result.get('success') else '❌'} {result.get('success')}")
    print(f"药品名称: {result.get('drug_name', keyword)}")
    print(f"找到供应商数: {result.get('total_found', len(result.get('providers', [])))}")
    
    if result.get('price_stats'):
        stats = result['price_stats']
        print(f"\n💰 价格统计:")
        print(f"  最低价: ¥{stats.get('min', 0):.2f}")
        print(f"  最高价: ¥{stats.get('max', 0):.2f}")
        print(f"  平均价: ¥{stats.get('avg', 0):.2f}")
        print(f"  供应商数: {stats.get('count', 0)}")
    
    providers = result.get('providers', [])
    if providers:
        print(f"\n📋 供应商价格列表（按价格排序）:")
        print(f"{'-'*60}")
        for i, p in enumerate(providers[:30], 1):
            source = p.get('source', '')
            source_tag = f" [{source}]" if source else ""
            print(f"  {i:2d}. {p.get('provider_name', '未知'):20s}: ¥{p.get('price', 0):8.2f}{source_tag}")
        
        if len(providers) > 30:
            print(f"  ... 还有 {len(providers) - 30} 个供应商")
    
    if result.get('error'):
        print(f"\n❌ 错误: {result.get('error')}")
    
    print(f"\n{'='*60}")


def crawl_search_results_sync(keyword: str, token: str = None, max_items: int = 10, headless: bool = True) -> Dict[str, Any]:
    """
    同步方式搜索并获取所有匹配的药品列表（不获取供应商价格）
    
    用于批量采集场景：先获取搜索结果，再逐个采集每个药品的供应商价格
    
    Args:
        keyword: 搜索关键词
        token: 登录Token
        max_items: 最多返回多少个药品
        headless: 是否无头模式
        
    Returns:
        搜索结果，包含:
        - success: 是否成功
        - items: 药品列表，每个包含 name, drug_id 等信息
        - total: 总数
    """
    async def search_only():
        crawler = YSBangPlaywrightCrawler(token=token, headless=headless)
        
        try:
            await crawler.start()
            
            # 搜索药品
            await crawler.page.goto('https://dian.ysbang.cn/', wait_until='networkidle')
            await crawler.page.wait_for_timeout(2000)
            
            # 输入搜索关键词
            search_input = await crawler.page.query_selector('input[placeholder*="搜索"]')
            if not search_input:
                return {'success': False, 'error': '未找到搜索框'}
            
            await search_input.fill(keyword)
            await crawler.page.wait_for_timeout(500)
            await search_input.press('Enter')
            await crawler.page.wait_for_timeout(3000)
            
            # 等待搜索结果加载
            try:
                await crawler.page.wait_for_selector('.drug-item, .goods-item, [class*="drug"], [class*="goods"]', timeout=10000)
            except:
                return {'success': False, 'error': '搜索结果加载超时'}
            
            # 提取搜索结果
            items = []
            
            # 尝试多种选择器
            selectors = [
                '.drug-item',
                '.goods-item', 
                '[class*="drug-card"]',
                '[class*="goods-card"]'
            ]
            
            for selector in selectors:
                elements = await crawler.page.query_selector_all(selector)
                if elements:
                    logger.info(f"找到 {len(elements)} 个药品元素（选择器: {selector}）")
                    
                    for idx, elem in enumerate(elements[:max_items]):
                        try:
                            # 提取药品信息
                            name_elem = await elem.query_selector('[class*="name"], [class*="title"], h3, h4')
                            name = await name_elem.inner_text() if name_elem else f'药品{idx+1}'
                            
                            # 尝试从链接中提取drugId
                            drug_id = None
                            link_elem = await elem.query_selector('a[href*="drugId"]')
                            if link_elem:
                                href = await link_elem.get_attribute('href')
                                if 'drugId=' in href:
                                    drug_id = int(href.split('drugId=')[1].split('&')[0])
                            
                            items.append({
                                'name': name.strip(),
                                'drug_id': drug_id
                            })
                        except Exception as e:
                            logger.warning(f"提取药品信息失败: {e}")
                            continue
                    
                    break
            
            if not items:
                return {'success': False, 'error': '未找到任何药品'}
            
            return {
                'success': True,
                'items': items,
                'total': len(items),
                'keyword': keyword
            }
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            await crawler.close()
    
    return asyncio.run(search_only())
