"""
API路径自动提取工具

从SPA网站的JS文件中自动提取API接口路径
"""
import re
import requests
from typing import List, Set
from urllib.parse import urljoin


class APIExtractor:
    """
    从前端JS文件中提取API路径
    
    使用方法:
        extractor = APIExtractor('https://dian.ysbang.cn')
        apis = extractor.extract_all()
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def extract_all(self) -> List[str]:
        """提取所有API路径"""
        # 1. 获取主页，找到JS文件
        js_urls = self._find_js_files()
        
        # 2. 从每个JS文件提取API
        all_apis = set()
        for js_url in js_urls:
            apis = self._extract_from_js(js_url)
            all_apis.update(apis)
        
        return sorted(all_apis)
    
    def _find_js_files(self) -> List[str]:
        """从主页HTML中找到JS文件URL"""
        try:
            resp = self.session.get(self.base_url, timeout=10)
            # 匹配JS文件URL
            pattern = r'src=["\']([^"\']*\.js)["\']'
            matches = re.findall(pattern, resp.text)
            
            js_urls = []
            for match in matches:
                if match.startswith('http'):
                    js_urls.append(match)
                else:
                    js_urls.append(urljoin(self.base_url, match))
            
            return js_urls
        except Exception as e:
            print(f"获取JS文件失败: {e}")
            return []
    
    def _extract_from_js(self, js_url: str) -> Set[str]:
        """从单个JS文件提取API路径"""
        apis = set()
        try:
            resp = self.session.get(js_url, timeout=30)
            content = resp.text
            
            # 模式1: 带版本号的API路径 /xxx/xxx/v123
            pattern1 = r'["\']/([\w-]+/[\w-]+/[\w/]+/v\d+)["\']'
            for match in re.findall(pattern1, content):
                apis.add(f'/{match}')
            
            # 模式2: /api/xxx 格式
            pattern2 = r'["\'](/api/[^"\']+)["\']'
            for match in re.findall(pattern2, content):
                if len(match) < 100:
                    apis.add(match)
            
            # 模式3: baseURL配置
            pattern3 = r'baseURL["\']?\s*[:=]\s*["\']([^"\']+)["\']'
            for match in re.findall(pattern3, content):
                print(f"发现baseURL: {match}")
            
        except Exception as e:
            print(f"解析JS失败 {js_url}: {e}")
        
        return apis
    
    def find_search_apis(self) -> List[str]:
        """找到搜索相关的API"""
        all_apis = self.extract_all()
        search_keywords = ['search', 'query', 'list', 'goods', 'drug', 'product']
        
        search_apis = []
        for api in all_apis:
            api_lower = api.lower()
            if any(kw in api_lower for kw in search_keywords):
                search_apis.append(api)
        
        return search_apis


if __name__ == '__main__':
    extractor = APIExtractor('https://dian.ysbang.cn')
    
    print("=== 所有API路径 ===")
    apis = extractor.extract_all()
    print(f"共找到 {len(apis)} 个API")
    
    print("\n=== 搜索相关API ===")
    search_apis = extractor.find_search_apis()
    for api in search_apis[:20]:
        print(f"  {api}")
