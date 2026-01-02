"""
Token管理工具

自动登录获取Token，处理Token过期问题
"""
import json
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict
import requests


class TokenManager:
    """
    Token管理器
    
    功能:
    1. 自动登录获取Token
    2. Token缓存和过期检测
    3. 自动刷新Token
    
    使用方法:
        manager = TokenManager()
        token = manager.get_valid_token(phone='13800138000', password='xxx')
    """
    
    # Token缓存文件
    TOKEN_CACHE_FILE = '.token_cache.json'
    
    # 药师帮登录API
    LOGIN_API = 'https://dian.ysbang.cn/ysb-user/api/auth/webLogin/v4270'
    
    # Token验证API
    VERIFY_API = 'https://dian.ysbang.cn/wholesale-drug/sales/getRegularSearchPurchaseListForPc/v5430'
    
    def __init__(self, cache_dir: str = '.'):
        self.cache_file = os.path.join(cache_dir, self.TOKEN_CACHE_FILE)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://dian.ysbang.cn',
            'Referer': 'https://dian.ysbang.cn/',
        })
    
    def get_valid_token(self, phone: str = None, password: str = None) -> Optional[str]:
        """
        获取有效的Token
        
        优先使用缓存，缓存无效时自动登录
        """
        # 1. 尝试从缓存获取
        cached_token = self._load_cached_token()
        if cached_token and self._verify_token(cached_token):
            print("✅ 使用缓存Token")
            return cached_token
        
        # 2. 缓存无效，尝试登录
        if phone and password:
            print("🔄 缓存Token无效，正在登录...")
            new_token = self._login(phone, password)
            if new_token:
                self._save_token(new_token)
                return new_token
        
        print("❌ 无法获取有效Token，请手动提供")
        return None
    
    def _login(self, phone: str, password: str) -> Optional[str]:
        """
        登录获取Token
        
        注意: 药师帮可能有验证码，此方法可能需要扩展
        """
        try:
            body = {
                'phone': phone,
                'password': password,
                'loginType': 1,  # 密码登录
            }
            
            resp = self.session.post(self.LOGIN_API, json=body, timeout=15)
            data = resp.json()
            
            if data.get('code') in ['0', 0]:
                token = data.get('data', {}).get('token')
                if token:
                    print(f"✅ 登录成功")
                    return token
            
            print(f"❌ 登录失败: {data.get('message')}")
            return None
            
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return None
    
    def _verify_token(self, token: str) -> bool:
        """验证Token是否有效"""
        try:
            # 同时在header和cookie中设置token
            headers = {
                'Token': token,
                'Content-Type': 'application/json',
                'Origin': 'https://dian.ysbang.cn',
                'Referer': 'https://dian.ysbang.cn/',
            }
            cookies = {'Token': token}
            
            resp = self.session.post(
                self.VERIFY_API,
                json={'keyword': '感冒', 'page': 1, 'pageSize': 1},
                headers=headers,
                cookies=cookies,
                timeout=10
            )
            data = resp.json()
            
            code = data.get('code')
            message = data.get('message', '')
            
            # 40020 = Token无效/需要登录
            if code == '40020' or '登录' in message:
                return False
            
            # 40001 + 成功 = 有效（药师帮特殊返回码）
            if code == '40001' and '成功' in message:
                return True
            
            # 0 = 成功
            if code in ['0', 0]:
                return True
            
            # 有数据返回也算有效
            if data.get('data'):
                return True
            
            return False
            
        except Exception as e:
            print(f"验证异常: {e}")
            return False
    
    def save_token_without_verify(self, token: str):
        """
        直接保存Token（不验证）
        用于用户确认Token有效的情况
        """
        self._save_token(token)
        print("✅ Token已保存（未验证）")
    
    def _load_cached_token(self) -> Optional[str]:
        """从缓存文件加载Token"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                
                # 检查是否过期（默认24小时）
                cached_time = datetime.fromisoformat(cache.get('time', '2000-01-01'))
                if datetime.now() - cached_time < timedelta(hours=24):
                    return cache.get('token')
        except Exception:
            pass
        return None
    
    def _save_token(self, token: str):
        """保存Token到缓存"""
        try:
            cache = {
                'token': token,
                'time': datetime.now().isoformat(),
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
            print(f"✅ Token已缓存")
        except Exception as e:
            print(f"⚠️ 缓存Token失败: {e}")
    
    def set_token_manually(self, token: str) -> bool:
        """
        手动设置Token（从浏览器复制）
        
        使用方法:
            manager.set_token_manually('your_token_here')
        """
        if self._verify_token(token):
            self._save_token(token)
            print("✅ Token有效并已缓存")
            return True
        else:
            print("❌ Token无效")
            return False


class TokenRefreshMiddleware:
    """
    Scrapy中间件：自动刷新Token
    
    在settings.py中配置:
    DOWNLOADER_MIDDLEWARES = {
        'scraper.utils.token_manager.TokenRefreshMiddleware': 100,
    }
    """
    
    def __init__(self):
        self.token_manager = TokenManager()
        self.current_token = None
    
    def process_response(self, request, response, spider):
        """检测Token过期并刷新"""
        try:
            data = json.loads(response.text)
            if data.get('code') == '40020':
                spider.logger.warning("Token过期，尝试刷新...")
                
                # 尝试获取新Token
                new_token = self.token_manager.get_valid_token()
                if new_token:
                    spider.token = new_token
                    # 重新发送请求
                    request.headers['Token'] = new_token
                    return request.replace(dont_filter=True)
        except:
            pass
        
        return response


if __name__ == '__main__':
    manager = TokenManager()
    
    # 方式1: 手动设置Token（推荐）
    # manager.set_token_manually('your_token_from_browser')
    
    # 方式2: 自动登录（可能需要验证码）
    # token = manager.get_valid_token(phone='13800138000', password='xxx')
    
    print("\n使用说明:")
    print("1. 从浏览器获取Token后，运行:")
    print("   manager.set_token_manually('your_token')")
    print("2. 或者配置账号密码自动登录")
