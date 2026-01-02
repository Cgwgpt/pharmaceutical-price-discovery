"""
自动登录工具
使用Selenium模拟浏览器登录药师帮，自动获取Token
"""
import json
import time
import os
from datetime import datetime
from typing import Optional, Dict, Tuple


class AutoLoginService:
    """
    自动登录服务
    
    使用Selenium模拟浏览器登录，自动获取Cookie和Token
    小白用户只需输入账号密码即可
    """
    
    TOKEN_CACHE_FILE = '.token_cache.json'
    LOGIN_URL = 'https://dian.ysbang.cn/#/login'
    
    def __init__(self):
        self.driver = None
    
    def login_and_get_token(self, phone: str, password: str, headless: bool = True) -> Tuple[bool, str, Dict]:
        """
        登录并获取Token
        
        Args:
            phone: 手机号
            password: 密码
            headless: 是否无头模式（后台运行）
            
        Returns:
            (成功, 消息, {token, cookies})
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
        except ImportError:
            return False, '请先安装: pip install selenium webdriver-manager', {}
        
        try:
            # 配置Chrome选项
            options = Options()
            if headless:
                options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            
            # 启动浏览器
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(10)
            
            # 打开登录页
            self.driver.get(self.LOGIN_URL)
            time.sleep(2)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 15)
            
            # 查找并填写手机号
            phone_input = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'input[placeholder*="手机号"], input[type="tel"], input[name="phone"]')
            ))
            phone_input.clear()
            phone_input.send_keys(phone)
            time.sleep(0.5)
            
            # 查找并填写密码
            password_input = self.driver.find_element(
                By.CSS_SELECTOR, 'input[type="password"], input[placeholder*="密码"]'
            )
            password_input.clear()
            password_input.send_keys(password)
            time.sleep(0.5)
            
            # 点击登录按钮
            login_btn = self.driver.find_element(
                By.CSS_SELECTOR, 'button[type="submit"], .login-btn, button:contains("登录")'
            )
            login_btn.click()
            
            # 等待登录完成（URL变化或出现特定元素）
            time.sleep(3)
            
            # 检查是否需要验证码
            try:
                captcha = self.driver.find_element(By.CSS_SELECTOR, '.captcha, .verify-code, [class*="captcha"]')
                if captcha.is_displayed():
                    return False, '需要验证码，请使用手动方式获取Token', {}
            except:
                pass
            
            # 检查登录错误
            try:
                error_msg = self.driver.find_element(By.CSS_SELECTOR, '.error-msg, .el-message--error, [class*="error"]')
                if error_msg.is_displayed():
                    return False, f'登录失败: {error_msg.text}', {}
            except:
                pass
            
            # 等待跳转到首页
            time.sleep(2)
            
            # 获取Cookie和Token
            cookies = self.driver.get_cookies()
            cookie_dict = {c['name']: c['value'] for c in cookies}
            
            # 从Cookie中提取Token
            token = cookie_dict.get('Token', '')
            
            # 如果Cookie中没有Token，尝试从localStorage获取
            if not token:
                token = self.driver.execute_script(
                    "return localStorage.getItem('token') || localStorage.getItem('Token') || ''"
                )
            
            # 如果还没有，尝试从sessionStorage获取
            if not token:
                token = self.driver.execute_script(
                    "return sessionStorage.getItem('token') || sessionStorage.getItem('Token') || ''"
                )
            
            if token:
                # 保存Token
                self._save_token(token, cookie_dict)
                return True, 'Token获取成功！', {'token': token, 'cookies': cookie_dict}
            else:
                # 可能登录成功但没找到Token，返回cookies让用户手动查看
                return False, '登录可能成功，但未找到Token。请检查账号密码是否正确。', {'cookies': cookie_dict}
                
        except Exception as e:
            return False, f'登录过程出错: {str(e)}', {}
        finally:
            if self.driver:
                self.driver.quit()
    
    def _save_token(self, token: str, cookies: Dict = None):
        """保存Token到缓存"""
        cache = {
            'token': token,
            'cookies': cookies or {},
            'time': datetime.now().isoformat()
        }
        with open(self.TOKEN_CACHE_FILE, 'w') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    
    def get_cached_token(self) -> Optional[str]:
        """获取缓存的Token"""
        try:
            if os.path.exists(self.TOKEN_CACHE_FILE):
                with open(self.TOKEN_CACHE_FILE, 'r') as f:
                    cache = json.load(f)
                return cache.get('token')
        except:
            pass
        return None


def quick_login(phone: str, password: str) -> Tuple[bool, str]:
    """
    快速登录获取Token
    
    用法:
        success, message = quick_login('13800138000', 'password')
    """
    service = AutoLoginService()
    success, message, data = service.login_and_get_token(phone, password)
    return success, message


if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 3:
        phone = sys.argv[1]
        password = sys.argv[2]
        success, msg, data = AutoLoginService().login_and_get_token(phone, password, headless=False)
        print(f"结果: {msg}")
        if data.get('token'):
            print(f"Token: {data['token']}")
    else:
        print("用法: python auto_login.py <手机号> <密码>")
