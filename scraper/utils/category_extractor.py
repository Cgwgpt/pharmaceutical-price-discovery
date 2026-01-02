"""
商品类别提取器
通过Playwright采集详情页，拦截API请求，获取批准文号和商品类别
"""
import asyncio
import json
import re
import logging
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page

logger = logging.getLogger(__name__)


class CategoryExtractor:
    """
    商品类别提取器
    
    通过Playwright访问药品详情页，拦截API请求，提取批准文号和商品类别
    """
    
    def __init__(self, token: str = None):
        self.token = token
        self.captured_apis = []
    
    async def extract_category_from_detail(
        self,
        drug_id: int,
        headless: bool = True,
        timeout: int = 30000
    ) -> Dict[str, Any]:
        """
        从详情页提取商品类别和批准文号
        
        Args:
            drug_id: 药品ID
            headless: 是否无头模式
            timeout: 超时时间（毫秒）
            
        Returns:
            {
                'success': bool,
                'drug_id': int,
                'category': str,  # drug/cosmetic/medical_device/health_product
                'approval_number': str,
                'detail': dict,  # 详细信息
                'api_data': dict,  # 拦截到的API数据
                'error': str
            }
        """
        result = {
            'success': False,
            'drug_id': drug_id,
            'category': None,
            'approval_number': None,
            'detail': {},
            'api_data': {},
            'error': None
        }
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                context = await browser.new_context()
                
                # 设置token
                if self.token:
                    await context.add_cookies([{
                        'name': 'Token',
                        'value': self.token,
                        'domain': 'dian.ysbang.cn',
                        'path': '/'
                    }])
                
                page = await context.new_page()
                
                # 拦截API请求
                self.captured_apis = []
                
                async def handle_response(response):
                    """拦截并记录API响应"""
                    url = response.url
                    
                    # 只关注药师帮的API
                    if 'dian.ysbang.cn' in url and '/wholesale-drug/' in url:
                        try:
                            if response.status == 200:
                                data = await response.json()
                                self.captured_apis.append({
                                    'url': url,
                                    'data': data
                                })
                                logger.debug(f"拦截API: {url}")
                        except:
                            pass
                
                page.on('response', handle_response)
                
                # 访问详情页
                url = f'https://dian.ysbang.cn/#/drug/{drug_id}'
                logger.info(f"访问详情页: {url}")
                
                await page.goto(url, wait_until='networkidle', timeout=timeout)
                
                # 等待页面加载完成 - 检查是否有药品详情内容
                try:
                    # 等待药品名称元素出现（根据实际页面结构调整）
                    await page.wait_for_selector('text=/.*/', timeout=5000)
                    await asyncio.sleep(3)  # 额外等待API请求完成
                    logger.info("页面加载完成")
                except:
                    logger.warning("等待页面元素超时，继续...")
                    await asyncio.sleep(5)  # 多等待一会儿
                
                # 分析拦截到的API数据
                logger.info(f"拦截到 {len(self.captured_apis)} 个API请求")
                
                # 保存所有拦截到的API URL（用于调试）
                result['captured_api_urls'] = [api['url'] for api in self.captured_apis]
                
                # 保存所有API数据到文件（调试用）
                try:
                    import json
                    with open(f'debug_api_{drug_id}.json', 'w', encoding='utf-8') as f:
                        json.dump(self.captured_apis, f, ensure_ascii=False, indent=2)
                    logger.info(f"API数据已保存到 debug_api_{drug_id}.json")
                except:
                    pass
                
                for api in self.captured_apis:
                    api_url = api['url']
                    api_data = api['data']
                    
                    logger.debug(f"分析API: {api_url}")
                    
                    # 查找批准文号字段
                    approval = self._find_approval_number(api_data)
                    if approval:
                        result['approval_number'] = approval
                        result['category'] = self._determine_category_by_approval(approval)
                        result['api_data'] = api_data
                        result['api_url'] = api_url
                        logger.info(f"✅ 找到批准文号: {approval} -> {result['category']}")
                        break
                
                # 如果API中没有找到，尝试从页面内容中提取
                if not result['approval_number']:
                    content = await page.content()
                    approval = self._extract_approval_from_html(content)
                    if approval:
                        result['approval_number'] = approval
                        result['category'] = self._determine_category_by_approval(approval)
                        logger.info(f"✅ 从HTML提取批准文号: {approval} -> {result['category']}")
                
                # 提取其他详细信息
                result['detail'] = await self._extract_detail_info(page)
                
                result['success'] = True
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"提取类别失败: {e}")
            result['error'] = str(e)
        
        return result
    
    def _find_approval_number(self, data: Any, path: str = '') -> Optional[str]:
        """
        递归查找批准文号字段
        
        Args:
            data: API返回的数据
            path: 当前路径（用于调试）
            
        Returns:
            批准文号或None
        """
        if isinstance(data, dict):
            # 检查常见的批准文号字段名
            approval_fields = [
                'approvalNumber', 'approval_number', 'approvalNo',
                'licenseNumber', 'license_number', 'licenseNo',
                'registrationNumber', 'registration_number',
                'certificateNumber', 'certificate_number',
                'approvalNum', 'licenseNum', 'registrationNum',
                'pzwh', 'pihao', 'zhunzi',  # 拼音
            ]
            
            for field in approval_fields:
                if field in data:
                    value = data[field]
                    if value and isinstance(value, str) and len(value) > 5:
                        # 验证是否是有效的批准文号格式
                        if self._is_valid_approval_number(value):
                            logger.debug(f"找到批准文号字段: {path}.{field} = {value}")
                            return value
            
            # 递归查找
            for key, value in data.items():
                result = self._find_approval_number(value, f"{path}.{key}")
                if result:
                    return result
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                result = self._find_approval_number(item, f"{path}[{i}]")
                if result:
                    return result
        
        return None
    
    def _is_valid_approval_number(self, text: str) -> bool:
        """验证是否是有效的批准文号格式"""
        patterns = [
            r'国药准字[HZSJB]\d{8}',
            r'国械注准\d+',
            r'国械注进\d+',
            r'卫妆准字\d+',
            r'国妆特字\d+',
            r'国食健字G?\d+',
            r'卫食健字\d+',
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _extract_approval_from_html(self, html: str) -> Optional[str]:
        """从HTML内容中提取批准文号"""
        patterns = [
            r'国药准字[HZSJB]\d{8}',
            r'国械注准\d+',
            r'国械注进\d+',
            r'卫妆准字\d+',
            r'国妆特字\d+',
            r'国食健字G?\d+',
            r'卫食健字\d+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(0)
        
        return None
    
    def _determine_category_by_approval(self, approval_number: str) -> str:
        """
        根据批准文号判断商品类别（最可靠的方法）
        
        批准文号格式：
        - 国药准字H/Z/S/J/B + 8位数字 = 药品
        - 国械注准/进 = 医疗器械
        - 卫妆准字/国妆特字 = 化妆品
        - 国食健字/卫食健字 = 保健品
        
        Returns:
            category: drug, medical_device, cosmetic, health_product
        """
        approval = approval_number.upper()
        
        # 药品：国药准字
        if re.match(r'国药准字[HZSJB]\d{8}', approval):
            return 'drug'
        
        # 医疗器械：国械注准、国械注进
        if re.match(r'国械注[准进]', approval):
            return 'medical_device'
        
        # 化妆品：卫妆准字、国妆特字
        if '妆' in approval:
            return 'cosmetic'
        
        # 保健品：国食健字、卫食健字
        if '食健' in approval:
            return 'health_product'
        
        return 'unknown'
    
    async def _extract_detail_info(self, page: Page) -> Dict[str, Any]:
        """提取详情页的其他信息"""
        detail = {}
        
        try:
            # 尝试提取常见字段
            # 这里可以根据实际页面结构添加更多提取逻辑
            title = await page.title()
            detail['page_title'] = title
            
            # 可以添加更多字段提取
            # detail['price'] = ...
            # detail['stock'] = ...
            
        except Exception as e:
            logger.debug(f"提取详情信息失败: {e}")
        
        return detail


def extract_category_sync(
    drug_id: int,
    token: str = None,
    headless: bool = True
) -> Dict[str, Any]:
    """
    同步版本的类别提取（方便调用）
    
    Args:
        drug_id: 药品ID
        token: 认证token
        headless: 是否无头模式
        
    Returns:
        提取结果
    """
    extractor = CategoryExtractor(token)
    return asyncio.run(extractor.extract_category_from_detail(drug_id, headless))


async def batch_extract_categories(
    drug_ids: list,
    token: str = None,
    headless: bool = True,
    max_concurrent: int = 3
) -> list:
    """
    批量提取商品类别
    
    Args:
        drug_ids: 药品ID列表
        token: 认证token
        headless: 是否无头模式
        max_concurrent: 最大并发数
        
    Returns:
        提取结果列表
    """
    extractor = CategoryExtractor(token)
    
    # 使用信号量控制并发
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def extract_with_limit(drug_id):
        async with semaphore:
            return await extractor.extract_category_from_detail(drug_id, headless)
    
    tasks = [extract_with_limit(drug_id) for drug_id in drug_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results


if __name__ == '__main__':
    # 测试
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python category_extractor.py <drug_id>")
        print("示例: python category_extractor.py 138595")
        sys.exit(1)
    
    drug_id = int(sys.argv[1])
    
    # 读取token
    try:
        with open('.token_cache.json', 'r') as f:
            token = json.load(f)['token']
    except:
        token = None
        print("⚠️  未找到token，可能无法访问详情页")
    
    print(f"正在提取 drugId={drug_id} 的类别信息...")
    print("=" * 70)
    
    result = extract_category_sync(drug_id, token, headless=False)
    
    print(f"\n结果:")
    print(f"  成功: {result['success']}")
    print(f"  类别: {result['category']}")
    print(f"  批准文号: {result['approval_number']}")
    
    if result['api_data']:
        print(f"\n拦截到的API数据:")
        print(json.dumps(result['api_data'], ensure_ascii=False, indent=2)[:500])
    
    if result['error']:
        print(f"\n错误: {result['error']}")
