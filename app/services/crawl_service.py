"""
采集任务服务
实现药品列表管理和批量采集功能
"""
import json
import logging
import subprocess
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from app.models import Base, init_db

logger = logging.getLogger(__name__)


class CrawlTaskStatus(str, Enum):
    """采集任务状态"""
    PENDING = 'pending'      # 等待执行
    RUNNING = 'running'      # 执行中
    COMPLETED = 'completed'  # 已完成
    FAILED = 'failed'        # 失败
    CANCELLED = 'cancelled'  # 已取消


class DrugWatchList(Base):
    """药品监控列表模型"""
    __tablename__ = 'drug_watch_list'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(200), nullable=False, index=True)
    category = Column(String(100))  # 分类：感冒药、抗生素等
    priority = Column(Integer, default=0)  # 优先级：0-普通，1-重要，2-紧急
    is_active = Column(Boolean, default=True)
    last_crawled_at = Column(DateTime)
    crawl_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'keyword': self.keyword,
            'category': self.category,
            'priority': self.priority,
            'is_active': self.is_active,
            'last_crawled_at': self.last_crawled_at.isoformat() if self.last_crawled_at else None,
            'crawl_count': self.crawl_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CrawlTask(Base):
    """采集任务模型"""
    __tablename__ = 'crawl_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(200))
    keywords = Column(Text)  # JSON格式的关键词列表
    status = Column(String(20), default=CrawlTaskStatus.PENDING)
    total_keywords = Column(Integer, default=0)
    completed_keywords = Column(Integer, default=0)
    total_items = Column(Integer, default=0)  # 采集到的药品数
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'task_name': self.task_name,
            'keywords': json.loads(self.keywords) if self.keywords else [],
            'status': self.status,
            'total_keywords': self.total_keywords,
            'completed_keywords': self.completed_keywords,
            'total_items': self.total_items,
            'progress': round(self.completed_keywords / self.total_keywords * 100, 1) if self.total_keywords > 0 else 0,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CrawlService:
    """
    采集服务
    
    功能:
    - 药品监控列表管理
    - 批量采集任务
    - 采集进度跟踪
    """
    
    def __init__(self):
        self.engine, SessionLocal = init_db(DATABASE_URL)
        # 确保表存在
        DrugWatchList.__table__.create(self.engine, checkfirst=True)
        CrawlTask.__table__.create(self.engine, checkfirst=True)
        self.session = SessionLocal()
        self._running_tasks = {}  # 正在运行的任务
    
    def __del__(self):
        if hasattr(self, 'session') and self.session:
            self.session.close()
    
    # ==================== 监控列表管理 ====================
    
    def add_to_watch_list(
        self,
        keyword: str,
        category: str = None,
        priority: int = 0
    ) -> DrugWatchList:
        """
        添加药品到监控列表
        
        Args:
            keyword: 药品关键词
            category: 分类
            priority: 优先级
            
        Returns:
            监控列表项
        """
        # 检查是否已存在
        existing = self.session.query(DrugWatchList).filter(
            DrugWatchList.keyword == keyword
        ).first()
        
        if existing:
            existing.is_active = True
            existing.category = category or existing.category
            existing.priority = priority
            existing.updated_at = datetime.utcnow()
            self.session.commit()
            return existing
        
        item = DrugWatchList(
            keyword=keyword,
            category=category,
            priority=priority
        )
        self.session.add(item)
        self.session.commit()
        
        logger.info(f"添加到监控列表: {keyword}")
        return item
    
    def add_batch_to_watch_list(
        self,
        keywords: List[str],
        category: str = None
    ) -> int:
        """
        批量添加药品到监控列表
        
        Args:
            keywords: 关键词列表
            category: 分类
            
        Returns:
            添加数量
        """
        count = 0
        for keyword in keywords:
            keyword = keyword.strip()
            if keyword:
                self.add_to_watch_list(keyword, category)
                count += 1
        return count
    
    def remove_from_watch_list(self, keyword_id: int) -> bool:
        """从监控列表移除"""
        item = self.session.query(DrugWatchList).filter(
            DrugWatchList.id == keyword_id
        ).first()
        
        if item:
            item.is_active = False
            self.session.commit()
            return True
        return False
    
    def get_watch_list(
        self,
        category: str = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取监控列表
        
        Args:
            category: 分类筛选
            active_only: 仅返回激活的
            
        Returns:
            监控列表
        """
        query = self.session.query(DrugWatchList)
        
        if active_only:
            query = query.filter(DrugWatchList.is_active == True)
        if category:
            query = query.filter(DrugWatchList.category == category)
        
        items = query.order_by(
            DrugWatchList.priority.desc(),
            DrugWatchList.keyword
        ).all()
        
        return [item.to_dict() for item in items]
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        categories = self.session.query(DrugWatchList.category).filter(
            DrugWatchList.category.isnot(None),
            DrugWatchList.is_active == True
        ).distinct().all()
        
        return [c[0] for c in categories if c[0]]
    
    # ==================== 采集任务管理 ====================
    
    def create_crawl_task(
        self,
        keywords: List[str] = None,
        task_name: str = None,
        use_watch_list: bool = False,
        category: str = None
    ) -> CrawlTask:
        """
        创建采集任务
        
        Args:
            keywords: 关键词列表
            task_name: 任务名称
            use_watch_list: 使用监控列表
            category: 分类筛选（use_watch_list=True时有效）
            
        Returns:
            采集任务
        """
        if use_watch_list:
            watch_list = self.get_watch_list(category=category)
            keywords = [item['keyword'] for item in watch_list]
        
        if not keywords:
            raise ValueError("请提供要采集的药品关键词")
        
        task = CrawlTask(
            task_name=task_name or f"采集任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            keywords=json.dumps(keywords, ensure_ascii=False),
            total_keywords=len(keywords),
            status=CrawlTaskStatus.PENDING
        )
        
        self.session.add(task)
        self.session.commit()
        
        logger.info(f"创建采集任务: {task.task_name}, 共{len(keywords)}个关键词")
        return task
    
    def start_crawl_task(self, task_id: int, async_mode: bool = True) -> bool:
        """
        启动采集任务
        
        Args:
            task_id: 任务ID
            async_mode: 异步模式
            
        Returns:
            是否成功启动
        """
        task = self.session.query(CrawlTask).filter(CrawlTask.id == task_id).first()
        
        if not task:
            return False
        
        if task.status == CrawlTaskStatus.RUNNING:
            logger.warning(f"任务 {task_id} 已在运行中")
            return False
        
        task.status = CrawlTaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.completed_keywords = 0
        task.total_items = 0
        task.error_message = None
        self.session.commit()
        
        if async_mode:
            # 异步执行
            thread = threading.Thread(
                target=self._execute_crawl_task,
                args=(task_id,)
            )
            thread.start()
            self._running_tasks[task_id] = thread
        else:
            # 同步执行
            self._execute_crawl_task(task_id)
        
        return True
    
    def _execute_crawl_task(self, task_id: int):
        """执行采集任务"""
        # 重新获取session（线程安全）
        _, SessionLocal = init_db(DATABASE_URL)
        session = SessionLocal()
        
        try:
            task = session.query(CrawlTask).filter(CrawlTask.id == task_id).first()
            if not task:
                return
            
            keywords = json.loads(task.keywords)
            total_items = 0
            
            for i, keyword in enumerate(keywords):
                if task.status == CrawlTaskStatus.CANCELLED:
                    break
                
                logger.info(f"[{task_id}] 采集 ({i+1}/{len(keywords)}): {keyword}")
                
                try:
                    # 调用爬虫
                    items_count = self._crawl_keyword(keyword)
                    total_items += items_count
                    
                    # 更新监控列表
                    watch_item = session.query(DrugWatchList).filter(
                        DrugWatchList.keyword == keyword
                    ).first()
                    if watch_item:
                        watch_item.last_crawled_at = datetime.utcnow()
                        watch_item.crawl_count += 1
                    
                except Exception as e:
                    logger.error(f"采集 {keyword} 失败: {e}")
                
                # 更新进度
                task.completed_keywords = i + 1
                task.total_items = total_items
                session.commit()
            
            # 完成任务
            task.status = CrawlTaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            session.commit()
            
            logger.info(f"[{task_id}] 采集任务完成，共采集 {total_items} 条数据")
            
        except Exception as e:
            logger.error(f"[{task_id}] 采集任务失败: {e}")
            task = session.query(CrawlTask).filter(CrawlTask.id == task_id).first()
            if task:
                task.status = CrawlTaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
    
    def _crawl_keyword(self, keyword: str, max_pages: int = 3) -> int:
        """
        爬取单个关键词（直接调用API）
        
        Args:
            keyword: 关键词
            max_pages: 最大页数
            
        Returns:
            采集到的数据条数
        """
        import requests
        import json
        
        # 获取缓存的Token
        token = self._get_cached_token()
        if not token:
            logger.error("未配置Token，无法采集")
            return 0
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': 'https://dian.ysbang.cn',
            'Referer': 'https://dian.ysbang.cn/',
            'Token': token,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        cookies = {'Token': token}
        
        total_count = 0
        
        # 方法1: 使用常购常搜API获取药品聚合数据
        url = 'https://dian.ysbang.cn/wholesale-drug/sales/getRegularSearchPurchaseListForPc/v5430'
        try:
            for page in range(1, max_pages + 1):
                body = {'keyword': keyword, 'page': page, 'pageSize': 60}
                resp = requests.post(url, json=body, headers=headers, cookies=cookies, timeout=15)
                data = resp.json()
                
                code = data.get('code')
                if code == '40020':
                    logger.error(f"Token无效或已过期")
                    return total_count
                
                if code not in ['0', 0, '40001']:
                    logger.error(f"API错误: {data.get('message')}")
                    break
                
                items = data.get('data', [])
                if isinstance(items, dict):
                    items = items.get('list', [])
                
                if not items:
                    break
                
                # 保存到数据库
                count = self._save_items_to_db(items)
                total_count += count
                
                if len(items) < 60:  # 没有更多数据
                    break
        except Exception as e:
            logger.error(f"API爬取异常: {e}")
        
        # 方法2: 获取供应商列表，然后获取热销商品中的相关价格
        try:
            total_count += self._crawl_provider_prices(keyword, headers, cookies)
        except Exception as e:
            logger.error(f"供应商价格爬取异常: {e}")
        
        return total_count
    
    def _crawl_provider_prices(self, keyword: str, headers: dict, cookies: dict, max_providers: int = 50) -> int:
        """
        通过供应商热销商品获取具体价格
        
        API限制说明:
        - 药师帮PC端搜索API只返回聚合数据（min/max价格）
        - 要获取单个供应商价格，需要通过供应商热销商品API
        - 热销商品API只返回供应商的TOP热销商品，不是所有商品
        - 因此可能无法获取所有供应商的特定药品价格
        
        Args:
            keyword: 关键词
            headers: 请求头
            cookies: Cookie
            max_providers: 最大供应商数量
            
        Returns:
            采集到的数据条数
        """
        import requests
        
        total_count = 0
        
        # 1. 获取供应商列表（使用facetWholesaleListByProvider）
        url1 = 'https://dian.ysbang.cn/wholesale-drug/sales/facetWholesaleListByProvider/v4270'
        body1 = {'keyword': keyword, 'page': 1, 'pageSize': max_providers}
        
        try:
            resp = requests.post(url1, json=body1, headers=headers, cookies=cookies, timeout=15)
            data = resp.json()
            
            if data.get('code') not in ['0', 0, '40001']:
                return 0
            
            providers = data.get('data', {}).get('providers', [])
            if not providers:
                return 0
            
            logger.info(f"[{keyword}] 找到 {len(providers)} 个供应商，采集前 {min(len(providers), max_providers)} 个的热销商品")
            
            # 2. 遍历供应商，获取热销商品（增加pageSize以获取更多商品）
            url2 = 'https://dian.ysbang.cn/wholesale-drug/sales/getHotWholesalesForProvider/v4230'
            
            found_providers = []
            for provider in providers[:max_providers]:
                pid = provider.get('pid')
                pname = provider.get('abbreviation', provider.get('name', ''))
                
                # 增加pageSize到200，尝试获取更多热销商品
                body2 = {'providerId': pid, 'page': 1, 'pageSize': 200}
                resp2 = requests.post(url2, json=body2, headers=headers, cookies=cookies, timeout=15)
                data2 = resp2.json()
                
                if data2.get('code') not in ['0', 0, '40001']:
                    continue
                
                items = data2.get('data', [])
                if not items:
                    continue
                
                # 过滤与关键词相关的商品（更宽松的匹配）
                keyword_lower = keyword.lower()
                related_items = []
                for item in items:
                    drug_name = item.get('drugname', '').lower()
                    # 检查关键词是否在药品名称中
                    if keyword_lower in drug_name:
                        related_items.append(item)
                    # 或者检查药品名称是否包含关键词的主要部分（至少3个字符）
                    elif len(keyword_lower) >= 3 and keyword_lower[:3] in drug_name:
                        related_items.append(item)
                
                if related_items:
                    count = self._save_provider_items(related_items, pname)
                    total_count += count
                    found_providers.append(pname)
            
            if found_providers:
                logger.info(f"[{keyword}] 从 {len(found_providers)} 个供应商的热销商品中找到相关价格: {', '.join(found_providers[:5])}...")
            else:
                logger.info(f"[{keyword}] 未在供应商热销商品中找到相关价格（热销商品API限制）")
                    
        except Exception as e:
            logger.error(f"供应商价格爬取异常: {e}")
        
        return total_count
    
    def crawl_drug_provider_prices(self, drug_id: int, keyword: str = None) -> Dict[str, Any]:
        """
        获取特定药品的所有供应商价格
        
        注意: 由于API限制，只能获取供应商热销商品中的价格
        
        Args:
            drug_id: 药品ID（药师帮的drugId）
            keyword: 药品关键词（用于匹配）
            
        Returns:
            包含供应商价格列表的字典
        """
        import requests
        
        token = self._get_cached_token()
        if not token:
            return {'success': False, 'error': '未配置Token'}
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': 'https://dian.ysbang.cn',
            'Referer': 'https://dian.ysbang.cn/',
            'Token': token,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        cookies = {'Token': token}
        
        results = {
            'drug_id': drug_id,
            'keyword': keyword,
            'providers': [],
            'aggregated': None,
            'success': True
        }
        
        # 1. 获取聚合数据
        url1 = 'https://dian.ysbang.cn/wholesale-drug/sales/getRegularSearchPurchaseListForPc/v5430'
        body1 = {'drugId': drug_id, 'page': 1, 'pageSize': 10}
        
        try:
            resp1 = requests.post(url1, json=body1, headers=headers, cookies=cookies, timeout=15)
            data1 = resp1.json()
            
            if data1.get('code') in ['0', 0, '40001']:
                items = data1.get('data', [])
                if isinstance(items, dict):
                    items = items.get('list', [])
                
                for item in items:
                    drug = item.get('drug', item)
                    if drug.get('drugId') == drug_id:
                        results['aggregated'] = {
                            'name': drug.get('drugName'),
                            'min_price': drug.get('minprice'),
                            'max_price': drug.get('maxprice'),
                            'supplier_count': drug.get('wholesaleNum'),
                            'spec': drug.get('specification'),
                            'manufacturer': drug.get('factory')
                        }
                        if not keyword:
                            keyword = drug.get('drugName', '').split()[0]  # 取第一个词作为关键词
                        break
        except Exception as e:
            logger.error(f"获取聚合数据失败: {e}")
        
        # 2. 获取供应商列表
        url2 = 'https://dian.ysbang.cn/wholesale-drug/sales/facetWholesaleList/v4270'
        body2 = {'drugId': drug_id}
        
        try:
            resp2 = requests.post(url2, json=body2, headers=headers, cookies=cookies, timeout=15)
            data2 = resp2.json()
            
            if data2.get('code') not in ['0', 0, '40001']:
                return results
            
            providers = data2.get('data', {}).get('providers', [])
            results['total_providers'] = len(providers)
            
            # 3. 遍历供应商，获取热销商品中的价格
            url3 = 'https://dian.ysbang.cn/wholesale-drug/sales/getHotWholesalesForProvider/v4230'
            
            for provider in providers:
                pid = provider.get('pid')
                pname = provider.get('abbreviation', provider.get('name', ''))
                
                body3 = {'providerId': pid, 'page': 1, 'pageSize': 200}
                resp3 = requests.post(url3, json=body3, headers=headers, cookies=cookies, timeout=15)
                data3 = resp3.json()
                
                if data3.get('code') not in ['0', 0, '40001']:
                    continue
                
                items = data3.get('data', [])
                for item in items:
                    drug_name = item.get('drugname', '')
                    # 匹配药品
                    if keyword and keyword.lower() in drug_name.lower():
                        results['providers'].append({
                            'provider_id': pid,
                            'provider_name': pname,
                            'drug_name': drug_name,
                            'price': item.get('price'),
                            'wholesale_id': item.get('wholesaleid'),
                            'spec': item.get('specification'),
                            'manufacturer': item.get('manufacturer')
                        })
                        break
            
            results['found_providers'] = len(results['providers'])
            
        except Exception as e:
            logger.error(f"获取供应商价格失败: {e}")
            results['success'] = False
            results['error'] = str(e)
        
        return results
    
    def _clean_drug_name(self, drug_name: str) -> str:
        """
        清理药品名称，去掉促销前缀，但保留关键规格信息
        
        例如: "1盒包邮 片仔癀3g*1粒(RX)" -> "片仔癀3g*1粒(RX)"
        但要保留: "片仔癀3g*1粒" vs "片仔癀3g*10粒" 的区别
        """
        import re
        
        original_name = drug_name
        
        # 去掉 "N盒包邮 " 这样的前缀
        if '包邮' in drug_name:
            parts = drug_name.split('包邮')
            if len(parts) > 1:
                drug_name = parts[1].strip()
        
        # 去掉 "N免邮 " 格式的前缀
        drug_name = re.sub(r'^\d+免邮\s*', '', drug_name)
        
        # 去掉 [xxx] 格式的前缀（如 [特价]、[促销]）
        drug_name = re.sub(r'^\[.*?\]\s*', '', drug_name)
        
        # 去掉其他常见促销前缀
        prefixes = ['特价', '限时', '秒杀', '促销', '热卖', '爆款', '新品', '推荐']
        for prefix in prefixes:
            if drug_name.startswith(prefix):
                drug_name = drug_name[len(prefix):].strip()
        
        # 去掉开头的空格和特殊字符
        drug_name = drug_name.strip()
        
        return drug_name
    
    def _save_provider_items(self, items: list, provider_name: str) -> int:
        """保存供应商商品数据"""
        from app.models import Drug, PriceRecord, init_db
        
        _, SessionLocal = init_db(DATABASE_URL)
        session = SessionLocal()
        count = 0
        
        try:
            for item in items:
                drug_name = item.get('drugname', '')
                price = item.get('price')
                spec = item.get('specification', '')
                manufacturer = item.get('manufacturer', '')
                wholesale_id = item.get('wholesaleid', '')
                drug_id = item.get('drug_id', '')
                
                if not drug_name or not price:
                    continue
                
                try:
                    price = float(str(price).replace('¥', '').replace('￥', ''))
                except:
                    continue
                
                # 清理药品名称
                clean_name = self._clean_drug_name(drug_name)
                
                # 查找药品（先用清理后的名称，再用原名称）
                db_drug = session.query(Drug).filter(
                    Drug.name == clean_name,
                    Drug.specification == spec
                ).first()
                
                if not db_drug:
                    # 尝试用原名称查找
                    db_drug = session.query(Drug).filter(
                        Drug.name == drug_name,
                        Drug.specification == spec
                    ).first()
                
                if not db_drug:
                    # 创建新药品（使用清理后的名称）
                    db_drug = Drug(
                        name=clean_name if clean_name else drug_name,
                        specification=spec,
                        manufacturer=manufacturer,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(db_drug)
                    session.flush()
                
                # 构建来源名称
                source_name = f'药师帮-{provider_name}' if provider_name else '药师帮'
                source_url = f'https://dian.ysbang.cn/#/wholesale/{wholesale_id}' if wholesale_id else ''
                
                # 检查是否已存在
                existing = session.query(PriceRecord).filter(
                    PriceRecord.drug_id == db_drug.id,
                    PriceRecord.source_name == source_name,
                    PriceRecord.price == price
                ).first()
                
                if not existing:
                    price_record = PriceRecord(
                        drug_id=db_drug.id,
                        price=price,
                        source_url=source_url,
                        source_name=source_name,
                        crawled_at=datetime.utcnow()
                    )
                    session.add(price_record)
                    count += 1
            
            session.commit()
        except Exception as e:
            logger.error(f"保存供应商商品失败: {e}")
            session.rollback()
        finally:
            session.close()
        
        return count
    
    def _get_cached_token(self) -> str:
        """获取缓存的Token"""
        import os
        import json
        cache_file = '.token_cache.json'
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
                return cache.get('token', '')
        except:
            pass
        return ''
    
    def _save_items_to_db(self, items: list) -> int:
        """保存药品数据到数据库（保存所有价格记录，不去重）"""
        from app.models import Drug, PriceRecord, init_db
        
        _, SessionLocal = init_db(DATABASE_URL)
        session = SessionLocal()
        count = 0
        
        try:
            for item in items:
                drug = item.get('drug', item)
                name = drug.get('drugName', '')
                min_price = drug.get('minprice')
                max_price = drug.get('maxprice')
                spec = drug.get('specification', '')
                manufacturer = drug.get('factory', '')
                drug_id = drug.get('drugId', '')
                wholesale_num = drug.get('wholesaleNum', 1)  # 供应商数量
                
                if not name or not min_price:
                    continue
                
                try:
                    min_price = float(str(min_price).replace('¥', '').replace('￥', ''))
                    max_price = float(str(max_price).replace('¥', '').replace('￥', '')) if max_price else min_price
                except:
                    continue
                
                # 查找或创建药品
                db_drug = session.query(Drug).filter(
                    Drug.name == name,
                    Drug.specification == spec
                ).first()
                
                if not db_drug:
                    db_drug = Drug(
                        name=name,
                        specification=spec,
                        manufacturer=manufacturer,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(db_drug)
                    session.flush()
                
                # 添加最低价记录
                price_record = PriceRecord(
                    drug_id=db_drug.id,
                    price=min_price,
                    source_url=f'https://dian.ysbang.cn/#/drug/{drug_id}',
                    source_name=f'药师帮(最低价,{wholesale_num}家)',
                    crawled_at=datetime.utcnow()
                )
                session.add(price_record)
                count += 1
                
                # 如果最高价不同，也添加记录
                if max_price and abs(max_price - min_price) > 0.01:
                    price_record_max = PriceRecord(
                        drug_id=db_drug.id,
                        price=max_price,
                        source_url=f'https://dian.ysbang.cn/#/drug/{drug_id}',
                        source_name=f'药师帮(最高价,{wholesale_num}家)',
                        crawled_at=datetime.utcnow()
                    )
                    session.add(price_record_max)
                    count += 1
            
            session.commit()
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            session.rollback()
        finally:
            session.close()
        
        return count
    
    def _save_provider_items_to_db(self, items: list, keyword: str) -> int:
        """
        保存供应商级别的价格数据到数据库
        
        Args:
            items: 推荐流API返回的商品列表
            keyword: 搜索关键词（用于过滤相关商品）
            
        Returns:
            保存的记录数
        """
        from app.models import Drug, PriceRecord, init_db
        
        _, SessionLocal = init_db(DATABASE_URL)
        session = SessionLocal()
        count = 0
        
        # 关键词分词用于匹配
        keyword_parts = keyword.lower().replace(' ', '')
        
        try:
            for item in items:
                # 获取商品信息
                drug_name = item.get('drugname', '')
                price = item.get('price')
                provider_name = item.get('provider_name', item.get('abbreviation', ''))
                provider_id = item.get('provider_id', item.get('providerId', ''))
                spec = item.get('specification', '')
                manufacturer = item.get('manufacturer', '')
                wholesale_id = item.get('wholesaleid', '')
                drug_id = item.get('drug_id', '')
                
                if not drug_name or not price:
                    continue
                
                # 简单的关键词匹配过滤
                drug_name_lower = drug_name.lower().replace(' ', '')
                if keyword_parts not in drug_name_lower and drug_name_lower not in keyword_parts:
                    # 检查是否包含关键词的主要部分
                    if len(keyword_parts) > 2 and keyword_parts[:3] not in drug_name_lower:
                        continue
                
                try:
                    price = float(str(price).replace('¥', '').replace('￥', ''))
                except:
                    continue
                
                # 查找或创建药品
                db_drug = session.query(Drug).filter(
                    Drug.name == drug_name,
                    Drug.specification == spec
                ).first()
                
                if not db_drug:
                    db_drug = Drug(
                        name=drug_name,
                        specification=spec,
                        manufacturer=manufacturer,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(db_drug)
                    session.flush()
                
                # 构建来源名称（包含供应商信息）
                source_name = f'药师帮-{provider_name}' if provider_name else '药师帮'
                source_url = f'https://dian.ysbang.cn/#/drug/{drug_id}' if drug_id else f'https://dian.ysbang.cn/#/wholesale/{wholesale_id}'
                
                # 检查是否已存在相同的价格记录（同一药品、同一供应商、同一价格）
                existing = session.query(PriceRecord).filter(
                    PriceRecord.drug_id == db_drug.id,
                    PriceRecord.source_name == source_name,
                    PriceRecord.price == price
                ).first()
                
                if not existing:
                    price_record = PriceRecord(
                        drug_id=db_drug.id,
                        price=price,
                        source_url=source_url,
                        source_name=source_name,
                        crawled_at=datetime.utcnow()
                    )
                    session.add(price_record)
                    count += 1
            
            session.commit()
        except Exception as e:
            logger.error(f"保存供应商价格数据失败: {e}")
            session.rollback()
        finally:
            session.close()
        
        return count
    
    def cancel_crawl_task(self, task_id: int) -> bool:
        """取消采集任务"""
        task = self.session.query(CrawlTask).filter(CrawlTask.id == task_id).first()
        
        if not task:
            return False
        
        if task.status == CrawlTaskStatus.RUNNING:
            task.status = CrawlTaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            self.session.commit()
            return True
        
        return False
    
    def get_crawl_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取采集任务详情"""
        task = self.session.query(CrawlTask).filter(CrawlTask.id == task_id).first()
        return task.to_dict() if task else None
    
    def get_crawl_tasks(
        self,
        status: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取采集任务列表
        
        Args:
            status: 状态筛选
            limit: 返回数量
            
        Returns:
            任务列表
        """
        query = self.session.query(CrawlTask)
        
        if status:
            query = query.filter(CrawlTask.status == status)
        
        tasks = query.order_by(CrawlTask.created_at.desc()).limit(limit).all()
        
        return [task.to_dict() for task in tasks]
    
    def get_crawl_statistics(self) -> Dict[str, Any]:
        """获取采集统计"""
        from sqlalchemy import func
        
        total_tasks = self.session.query(func.count(CrawlTask.id)).scalar()
        completed_tasks = self.session.query(func.count(CrawlTask.id)).filter(
            CrawlTask.status == CrawlTaskStatus.COMPLETED
        ).scalar()
        total_items = self.session.query(func.sum(CrawlTask.total_items)).scalar() or 0
        
        watch_list_count = self.session.query(func.count(DrugWatchList.id)).filter(
            DrugWatchList.is_active == True
        ).scalar()
        
        # 今日采集
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_tasks = self.session.query(func.count(CrawlTask.id)).filter(
            CrawlTask.created_at >= today
        ).scalar()
        today_items = self.session.query(func.sum(CrawlTask.total_items)).filter(
            CrawlTask.created_at >= today
        ).scalar() or 0
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'total_items_crawled': total_items,
            'watch_list_count': watch_list_count,
            'today_tasks': today_tasks,
            'today_items': today_items
        }
    
    def quick_crawl(self, keywords: List[str], max_pages: int = 3) -> Dict[str, Any]:
        """
        快速采集（同步执行，适合少量关键词）
        
        Args:
            keywords: 关键词列表
            max_pages: 每个关键词最大页数
            
        Returns:
            采集结果
        """
        results = []
        total_items = 0
        
        for keyword in keywords:
            logger.info(f"快速采集: {keyword}")
            items_count = self._crawl_keyword(keyword, max_pages)
            total_items += items_count
            results.append({
                'keyword': keyword,
                'items_count': items_count,
                'success': items_count > 0
            })
        
        return {
            'keywords': keywords,
            'results': results,
            'total_items': total_items,
            'success_count': len([r for r in results if r['success']]),
            'crawled_at': datetime.now().isoformat()
        }
    
    # ==================== 智能采集策略 ====================
    
    def crawl_quick_mode(
        self,
        keyword: str,
        drug_id: int = None,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        快速模式：仅使用 API 获取热销商品价格
        
        适用场景:
        - 快速查询价格参考
        - 批量采集大量药品
        - 对数据完整性要求不高
        - 追求速度和效率
        
        特点:
        - 速度快（1-3秒）
        - 资源占用低
        - 获取热销供应商价格（通常1-10个）
        - 适合日常查询
        
        Args:
            keyword: 药品关键词
            drug_id: 药品ID（可选）
            save_to_db: 是否保存到数据库
            
        Returns:
            采集结果
        """
        result = {
            'keyword': keyword,
            'drug_id': drug_id,
            'success': False,
            'mode': 'quick',
            'method': 'api',
            'providers': [],
            'saved_count': 0,
            'error': None
        }
        
        logger.info(f"[快速模式] 采集: {keyword}")
        
        # 使用 API 采集
        providers = self._crawl_with_api_only(keyword, drug_id, max_providers=50)
        result['providers'] = providers
        
        # 保存到数据库
        if save_to_db and providers:
            saved = self._save_api_providers_to_db(providers, keyword)
            result['saved_count'] = saved
        
        result['success'] = len(providers) > 0
        
        if result['success']:
            logger.info(f"[快速模式] ✅ 找到 {len(providers)} 个热销供应商价格")
        else:
            logger.warning(f"[快速模式] ⚠️ 未找到供应商价格")
            result['error'] = '未找到热销商品价格，建议使用完整模式'
        
        return result
    
    def crawl_complete_mode(
        self,
        keyword: str,
        drug_id: int = None,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        完整模式：使用 Playwright 获取所有供应商价格
        
        适用场景:
        - 需要完整的供应商价格数据
        - 重要药品的采购决策
        - 价格对比分析
        - 追求数据完整性
        
        特点:
        - 数据完整（通常50-100个供应商）
        - 速度较慢（10-30秒）
        - 资源占用高（需要启动浏览器）
        - 适合重要决策
        
        Args:
            keyword: 药品关键词
            drug_id: 药品ID（可选）
            save_to_db: 是否保存到数据库
            
        Returns:
            采集结果
        """
        result = {
            'keyword': keyword,
            'drug_id': drug_id,
            'success': False,
            'mode': 'complete',
            'method': 'playwright',
            'providers': [],
            'saved_count': 0,
            'error': None
        }
        
        logger.info(f"[完整模式] 采集: {keyword}")
        
        # 使用 Playwright 采集
        pw_result = self.crawl_with_playwright(keyword, drug_id, headless=True, save_to_db=save_to_db)
        
        result['success'] = pw_result.get('success', False)
        result['providers'] = pw_result.get('providers', [])
        result['saved_count'] = pw_result.get('saved_count', 0)
        result['error'] = pw_result.get('error')
        
        if result['success']:
            logger.info(f"[完整模式] ✅ 找到 {len(result['providers'])} 个供应商价格")
        else:
            logger.error(f"[完整模式] ❌ 采集失败: {result['error']}")
        
        return result
    
    def crawl_with_smart_strategy(
        self,
        keyword: str,
        drug_id: int = None,
        force_playwright: bool = False,
        min_providers: int = 5,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        智能模式：API 优先，Playwright 作为备选（推荐）
        
        适用场景:
        - 不确定数据量的情况
        - 希望平衡速度和完整性
        - 自动化采集任务
        - 大多数日常使用
        
        策略:
        1. 优先使用 API 采集（快速）
        2. 如果 API 数据不足（供应商数量 < min_providers），使用 Playwright 补充
        3. 如果 force_playwright=True，直接使用 Playwright
        
        特点:
        - 自动决策
        - 性能最优
        - 数据充足时快速，不足时完整
        - 适合大多数场景
        
        Args:
            keyword: 药品关键词
            drug_id: 药品ID（可选）
            force_playwright: 强制使用 Playwright
            min_providers: 最小供应商数量阈值
            save_to_db: 是否保存到数据库
            
        Returns:
            采集结果，包含:
            - success: 是否成功
            - mode: 模式 ('smart')
            - method: 使用的方法 ('api', 'playwright', 'hybrid')
            - providers: 供应商价格列表
            - stats: 统计信息
        """
        result = {
            'keyword': keyword,
            'drug_id': drug_id,
            'success': False,
            'mode': 'smart',
            'method': None,
            'providers': [],
            'api_count': 0,
            'playwright_count': 0,
            'saved_count': 0,
            'error': None
        }
        
        # 强制使用 Playwright
        if force_playwright:
            logger.info(f"[{keyword}] 🎭 强制使用 Playwright 采集")
            pw_result = self.crawl_with_playwright(keyword, drug_id, headless=True, save_to_db=save_to_db)
            result.update({
                'success': pw_result.get('success', False),
                'method': 'playwright',
                'providers': pw_result.get('providers', []),
                'playwright_count': len(pw_result.get('providers', [])),
                'saved_count': pw_result.get('saved_count', 0),
                'error': pw_result.get('error')
            })
            return result
        
        # 策略1: 优先使用 API
        logger.info(f"[{keyword}] 📡 步骤1: 使用 API 采集")
        api_providers = self._crawl_with_api_only(keyword, drug_id)
        result['api_count'] = len(api_providers)
        result['providers'] = api_providers
        
        # 保存 API 数据到数据库
        if save_to_db and api_providers:
            saved = self._save_api_providers_to_db(api_providers, keyword)
            result['saved_count'] = saved
        
        # 检查 API 数据是否充足
        if len(api_providers) >= min_providers:
            logger.info(f"[{keyword}] ✅ API 数据充足 ({len(api_providers)} 个供应商)，无需 Playwright")
            result.update({
                'success': True,
                'method': 'api'
            })
            return result
        
        # 策略2: API 数据不足，使用 Playwright 补充
        logger.info(f"[{keyword}] ⚠️  API 数据不足 ({len(api_providers)} < {min_providers})，使用 Playwright 补充")
        
        try:
            pw_result = self.crawl_with_playwright(keyword, drug_id, headless=True, save_to_db=save_to_db)
            
            if pw_result.get('success'):
                pw_providers = pw_result.get('providers', [])
                
                # 合并结果（去重）
                existing_names = {p.get('provider_name', '') for p in api_providers}
                new_providers = [
                    p for p in pw_providers 
                    if p.get('provider_name', '') not in existing_names
                ]
                
                result['providers'].extend(new_providers)
                result['playwright_count'] = len(new_providers)
                result['saved_count'] += pw_result.get('saved_count', 0)
                result['method'] = 'hybrid' if api_providers else 'playwright'
                result['success'] = True
                
                logger.info(f"[{keyword}] ✅ 混合采集完成: API {len(api_providers)} + Playwright {len(new_providers)} = {len(result['providers'])} 个供应商")
            else:
                logger.warning(f"[{keyword}] ❌ Playwright 采集失败: {pw_result.get('error')}")
                result['method'] = 'api'
                result['success'] = len(api_providers) > 0
                result['error'] = f"API 数据不足，Playwright 补充失败: {pw_result.get('error')}"
                
        except Exception as e:
            logger.error(f"[{keyword}] ❌ Playwright 补充异常: {e}")
            result['method'] = 'api'
            result['success'] = len(api_providers) > 0
            result['error'] = f"Playwright 补充异常: {str(e)}"
        
        return result
    
    def _crawl_with_api_only(
        self,
        keyword: str,
        drug_id: int = None,
        max_providers: int = 50
    ) -> List[Dict[str, Any]]:
        """
        仅使用 API 采集供应商价格
        
        Args:
            keyword: 药品关键词
            drug_id: 药品ID（可选）
            max_providers: 最大供应商数量
            
        Returns:
            供应商价格列表
        """
        import requests
        
        token = self._get_cached_token()
        if not token:
            logger.error("未配置Token，无法采集")
            return []
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Origin': 'https://dian.ysbang.cn',
            'Referer': 'https://dian.ysbang.cn/',
            'Token': token,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        cookies = {'Token': token}
        
        providers = []
        
        # 1. 获取供应商列表
        url1 = 'https://dian.ysbang.cn/wholesale-drug/sales/facetWholesaleListByProvider/v4270'
        body1 = {'keyword': keyword, 'page': 1, 'pageSize': max_providers}
        if drug_id:
            body1['drugId'] = drug_id
        
        try:
            resp = requests.post(url1, json=body1, headers=headers, cookies=cookies, timeout=15)
            data = resp.json()
            
            if data.get('code') not in ['0', 0, '40001']:
                logger.warning(f"API 返回错误: {data.get('message')}")
                return []
            
            provider_list = data.get('data', {}).get('providers', [])
            if not provider_list:
                logger.info(f"[{keyword}] 未找到供应商")
                return []
            
            logger.info(f"[{keyword}] 找到 {len(provider_list)} 个供应商")
            
            # 2. 遍历供应商，获取热销商品中的价格
            url2 = 'https://dian.ysbang.cn/wholesale-drug/sales/getHotWholesalesForProvider/v4230'
            
            for provider in provider_list[:max_providers]:
                pid = provider.get('pid')
                pname = provider.get('abbreviation', provider.get('name', ''))
                
                body2 = {'providerId': pid, 'page': 1, 'pageSize': 200}
                resp2 = requests.post(url2, json=body2, headers=headers, cookies=cookies, timeout=15)
                data2 = resp2.json()
                
                if data2.get('code') not in ['0', 0, '40001']:
                    continue
                
                items = data2.get('data', [])
                if not items:
                    continue
                
                # 过滤与关键词相关的商品
                keyword_lower = keyword.lower()
                for item in items:
                    drug_name = item.get('drugname', '')
                    if keyword_lower in drug_name.lower():
                        try:
                            price = float(item.get('price', 0))
                            if price > 0:
                                providers.append({
                                    'provider_id': pid,
                                    'provider_name': pname,
                                    'drug_name': drug_name,
                                    'price': price,
                                    'specification': item.get('specification', ''),
                                    'manufacturer': item.get('manufacturer', ''),
                                    'wholesale_id': item.get('wholesaleid', ''),
                                    'source': 'api'
                                })
                                break  # 每个供应商只取一个匹配的商品
                        except (ValueError, TypeError):
                            continue
            
            logger.info(f"[{keyword}] 📡 API 采集到 {len(providers)} 个供应商价格")
            
        except Exception as e:
            logger.error(f"[{keyword}] API 采集异常: {e}")
        
        return providers
    
    def _save_api_providers_to_db(self, providers: List[Dict[str, Any]], keyword: str, use_playwright_category: bool = False) -> int:
        """
        保存 API 采集的供应商价格到数据库
        
        Args:
            providers: 供应商价格列表
            keyword: 搜索关键词
            use_playwright_category: 是否使用Playwright精确提取类别（慢但准确）
            
        Returns:
            保存的记录数
        """
        from app.models import Drug, PriceRecord
        
        _, SessionLocal = init_db(DATABASE_URL)
        session = SessionLocal()
        count = 0
        
        # 如果启用Playwright，批量提取类别
        category_cache = {}
        if use_playwright_category:
            drug_ids = list(set([p.get('drug_id') for p in providers if p.get('drug_id')]))
            if drug_ids:
                logger.info(f"[Playwright] 批量提取 {len(drug_ids)} 个商品的类别...")
                category_cache = self._batch_extract_categories_pw(drug_ids[:10])  # 限制数量
        
        try:
            for provider in providers:
                drug_name = provider.get('drug_name', '')
                price = provider.get('price', 0)
                provider_name = provider.get('provider_name', '')
                spec = provider.get('specification', '')
                manufacturer = provider.get('manufacturer', '')
                drug_id = provider.get('drug_id')
                category = provider.get('category', 'drug')  # 商品类别
                approval_number = provider.get('approval_number')  # 批准文号
                
                if not drug_name or not price or price <= 0:
                    continue
                
                # 清理药品名称（保留规格信息）
                clean_name = self._clean_drug_name(drug_name)
                
                # 使用Playwright提取的类别（如果有）
                if use_playwright_category and drug_id in category_cache:
                    pw_result = category_cache[drug_id]
                    if pw_result.get('success'):
                        category = pw_result.get('category', category)
                        approval_number = pw_result.get('approval_number', approval_number)
                        logger.info(f"[Playwright] {clean_name}: {category} ({approval_number})")
                
                # 提取商品类别（如果API没有提供且没有用Playwright）
                if category == 'drug' and not approval_number:
                    result = self._detect_product_category(clean_name, manufacturer)
                    category = result['category']
                    confidence = result.get('confidence', 0.5)
                    reason = result.get('reason', '')
                    
                    if confidence < 0.8:
                        logger.info(f"[低置信度] {clean_name}: {category} (置信度={confidence:.2f}, 原因={reason})")
                
                # 查找或创建药品（严格匹配：名称+规格+厂家）
                db_drug = session.query(Drug).filter(
                    Drug.name == clean_name,
                    Drug.specification == spec,
                    Drug.manufacturer == manufacturer
                ).first()
                
                if not db_drug:
                    # 如果没有厂家信息，尝试只用名称+规格匹配
                    if not manufacturer:
                        db_drug = session.query(Drug).filter(
                            Drug.name == clean_name,
                            Drug.specification == spec
                        ).first()
                    
                    if not db_drug:
                        # 创建新药品
                        db_drug = Drug(
                            name=clean_name,
                            specification=spec,
                            manufacturer=manufacturer,
                            category=category,
                            approval_number=approval_number,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        session.add(db_drug)
                        session.flush()
                        logger.info(f"[新增商品] {category}: {clean_name} {spec} - {manufacturer}")
                else:
                    # 更新类别和批准文号（如果之前没有）
                    if not db_drug.category or db_drug.category == 'drug':
                        db_drug.category = category
                    if not db_drug.approval_number and approval_number:
                        db_drug.approval_number = approval_number
                
                # 构建来源名称
                source_name = f'药师帮-{provider_name}' if provider_name else '药师帮'
                
                # 检查是否已存在
                existing = session.query(PriceRecord).filter(
                    PriceRecord.drug_id == db_drug.id,
                    PriceRecord.source_name == source_name,
                    PriceRecord.price == price
                ).first()
                
                if not existing:
                    price_record = PriceRecord(
                        drug_id=db_drug.id,
                        price=price,
                        source_url='https://dian.ysbang.cn/',
                        source_name=source_name,
                        crawled_at=datetime.utcnow()
                    )
                    session.add(price_record)
                    count += 1
            
            session.commit()
            
            # 标注异常价格
            if count > 0:
                self._mark_price_outliers(session)
            
            logger.info(f"[API] 保存了 {count} 条价格记录")
            
        except Exception as e:
            logger.error(f"[API] 保存数据失败: {e}")
            session.rollback()
        finally:
            session.close()
        
        return count
    
    def _batch_extract_categories_pw(self, drug_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        使用Playwright批量提取商品类别
        
        Args:
            drug_ids: 药品ID列表
            
        Returns:
            {drug_id: {success, category, approval_number, ...}}
        """
        try:
            from scraper.utils.category_extractor import batch_extract_categories
            
            token = self._get_cached_token()
            
            # 异步批量提取
            import asyncio
            results = asyncio.run(batch_extract_categories(
                drug_ids,
                token=token,
                headless=True,
                max_concurrent=2  # 控制并发数
            ))
            
            # 转换为字典
            category_map = {}
            for i, drug_id in enumerate(drug_ids):
                if i < len(results) and not isinstance(results[i], Exception):
                    category_map[drug_id] = results[i]
            
            return category_map
            
        except Exception as e:
            logger.error(f"[Playwright] 批量提取类别失败: {e}")
            return {}
    
    def _detect_product_category(self, product_name: str, manufacturer: str = '') -> dict:
        """
        根据商品名称和厂家检测商品类别（改进版）
        
        Args:
            product_name: 商品名称
            manufacturer: 厂家名称（可选）
            
        Returns:
            {
                'category': str,  # drug/cosmetic/medical_device/health_product
                'confidence': float,  # 0.0-1.0
                'reason': str  # 识别依据
            }
        """
        name_lower = product_name.lower()
        mfr_lower = manufacturer.lower() if manufacturer else ''
        
        # 优先级1: 处方药/OTC标识（最高优先级，置信度100%）
        if '(rx)' in name_lower or '（rx）' in name_lower:
            return {'category': 'drug', 'confidence': 1.0, 'reason': '处方药标识(RX)'}
        
        if '(otc)' in name_lower or 'otc' in name_lower:
            return {'category': 'drug', 'confidence': 1.0, 'reason': 'OTC标识'}
        
        # 优先级2: 厂家信息（高置信度）
        if '化妆品' in mfr_lower:
            return {'category': 'cosmetic', 'confidence': 0.95, 'reason': '化妆品厂家'}
        
        if '医疗器械' in mfr_lower:
            return {'category': 'medical_device', 'confidence': 0.95, 'reason': '医疗器械厂家'}
        
        # 优先级3: 高置信度关键词（精确匹配）
        # 化妆品 - 使用更精确的关键词
        cosmetic_high = ['珍珠霜', '珍珠膏', '面霜', '乳液', '精华液', 
                         '洗面奶', '面膜', '眼霜', '护肤水', '化妆水', '皇后牌']
        for keyword in cosmetic_high:
            if keyword in name_lower:
                return {'category': 'cosmetic', 'confidence': 0.9, 'reason': f'化妆品关键词: {keyword}'}
        
        # 医疗器械 - 明确的器械名称
        device_high = ['血糖仪', '血压计', '体温计', '雾化器', '医用口罩', 
                       '外科口罩', '注射器', '输液器', '导尿管', '轮椅', '创可贴']
        for keyword in device_high:
            if keyword in name_lower:
                return {'category': 'medical_device', 'confidence': 0.9, 'reason': f'医疗器械: {keyword}'}
        
        # 优先级4: 药品剂型（中高置信度）
        drug_forms = ['片', '胶囊', '颗粒', '口服液', '注射液', '注射剂',
                      '软膏', '乳膏', '贴剂', '滴眼液', '滴剂', '糖浆',
                      '丸', '散', '膏药', '栓剂', '喷雾剂', '混悬剂']
        for form in drug_forms:
            if form in name_lower:
                return {'category': 'drug', 'confidence': 0.85, 'reason': f'药品剂型: {form}'}
        
        # 优先级5: 保健品关键词（需要排除药品）
        # 只有在不包含药品剂型的情况下才判定为保健品
        health_keywords = ['益生菌软糖', '蛋白粉', '鱼油', '保健食品', '营养品']
        for keyword in health_keywords:
            if keyword in name_lower:
                return {'category': 'health_product', 'confidence': 0.8, 'reason': f'保健品: {keyword}'}
        
        # 优先级6: 维生素类（需要更多上下文判断）
        if '维生素' in name_lower:
            # 如果有剂型词，判定为药品
            if any(form in name_lower for form in ['片', '胶囊', '滴剂', '口服液', '颗粒']):
                return {'category': 'drug', 'confidence': 0.75, 'reason': '维生素类药品（含剂型）'}
            else:
                return {'category': 'health_product', 'confidence': 0.6, 'reason': '维生素类保健品'}
        
        # 优先级7: 医疗器械 - 低置信度
        device_low = ['口罩', '手套', '纱布', '绷带', '拐杖']
        for keyword in device_low:
            if keyword in name_lower:
                return {'category': 'medical_device', 'confidence': 0.7, 'reason': f'医疗用品: {keyword}'}
        
        # 默认: 药品（低置信度）
        return {'category': 'drug', 'confidence': 0.5, 'reason': '默认分类'}
    
    def _mark_price_outliers(self, session) -> int:
        """
        标注异常价格
        
        对每个药品的价格进行统计分析，标注异常值
        
        Args:
            session: 数据库会话
            
        Returns:
            标注的异常价格数量
        """
        from sqlalchemy import func
        from app.models import Drug, PriceRecord
        
        marked_count = 0
        
        # 获取所有有价格记录的药品
        drugs = session.query(Drug).join(PriceRecord).group_by(Drug.id).all()
        
        for drug in drugs:
            # 获取该药品的所有最新价格
            prices = session.query(PriceRecord).filter(
                PriceRecord.drug_id == drug.id
            ).all()
            
            if len(prices) < 3:
                continue
            
            price_values = [float(p.price) for p in prices]
            price_values.sort()
            
            # 1. 标注占位价格
            placeholder_prices = [9999, 99999, 999999, 9.99, 99.99]
            for record in prices:
                if float(record.price) in placeholder_prices:
                    record.is_outlier = 2
                    record.outlier_reason = '占位价格'
                    marked_count += 1
            
            # 2. 使用IQR方法标注离群值
            n = len(price_values)
            if n >= 5:
                q1_idx = n // 4
                q3_idx = (3 * n) // 4
                q1 = price_values[q1_idx]
                q3 = price_values[q3_idx]
                iqr = q3 - q1
                
                if iqr > 0:
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    for record in prices:
                        if record.is_outlier != 0:  # 已标注的跳过
                            continue
                        
                        price_val = float(record.price)
                        if price_val < lower_bound:
                            record.is_outlier = -1
                            record.outlier_reason = f'异常低价 (低于 ¥{lower_bound:.2f})'
                            marked_count += 1
                        elif price_val > upper_bound:
                            record.is_outlier = 1
                            record.outlier_reason = f'异常高价 (高于 ¥{upper_bound:.2f})'
                            marked_count += 1
        
        session.commit()
        
        if marked_count > 0:
            logger.info(f"[价格标注] 标注了 {marked_count} 条异常价格")
        
        return marked_count
    
    # ==================== Playwright 采集 ====================

    def crawl_with_playwright(
        self,
        keyword: str,
        drug_id: int = None,
        max_items: int = 10,
        headless: bool = True,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        使用 Playwright 浏览器自动化爬取供应商价格
        
        这个方法可以获取每个供应商的具体价格，突破API聚合数据的限制
        
        工作原理:
        1. 使用 Playwright 打开浏览器
        2. 拦截页面发出的 API 请求，直接获取 JSON 数据
        3. 从 API 响应中提取供应商价格信息
        
        Args:
            keyword: 搜索关键词
            drug_id: 药品ID（强烈建议提供，可获取该药品的所有供应商价格）
            max_items: 最大处理商品数量
            headless: 是否无头模式运行
            save_to_db: 是否保存到数据库
            
        Returns:
            爬取结果
        """
        try:
            from scraper.utils.playwright_crawler import crawl_drug_detail_sync
        except ImportError:
            return {
                'success': False,
                'error': 'Playwright 未安装，请运行: pip install playwright && playwright install chromium'
            }
        
        logger.info(f"[Playwright] 开始爬取: {keyword}" + (f" (drugId={drug_id})" if drug_id else ""))
        
        # 获取Token
        token = self._get_cached_token()
        
        # 执行爬取 - 使用 crawl_drug_detail_sync 获取单个药品的所有供应商价格
        result = crawl_drug_detail_sync(
            keyword=keyword,
            drug_id=drug_id,
            token=token,
            max_providers=max_items * 10,  # 每个药品可能有多个供应商
            headless=headless
        )
        
        # 保存到数据库
        if save_to_db and result.get('success'):
            saved_count = self._save_playwright_results(result, keyword)
            result['saved_count'] = saved_count
        
        return result
    
    def _save_playwright_results(self, result: Dict[str, Any], keyword: str = None) -> int:
        """
        保存 Playwright 爬取结果到数据库
        
        Args:
            result: Playwright 爬取结果
            keyword: 搜索关键词（用于药品名称）
            
        Returns:
            新增的价格记录数量
        """
        from app.models import Drug, PriceRecord, init_db
        
        _, SessionLocal = init_db(DATABASE_URL)
        session = SessionLocal()
        count = 0
        skipped = 0
        
        try:
            # 处理 providers 格式（单个药品的所有供应商）
            providers = result.get('providers', [])
            drug_name = result.get('drug_name', keyword or '')
            
            if providers:
                # 清理药品名称
                clean_name = self._clean_drug_name(drug_name)
                
                # 查找药品 - 使用模糊匹配
                db_drug = session.query(Drug).filter(
                    Drug.name.like(f'%{clean_name}%')
                ).first()
                
                if not db_drug:
                    # 如果没找到，创建新药品
                    db_drug = Drug(
                        name=clean_name,
                        specification='',
                        manufacturer='',
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(db_drug)
                    session.flush()
                
                logger.info(f"[Playwright] 保存到药品: {db_drug.name} (ID={db_drug.id})")
                
                # 保存每个供应商的价格
                for provider in providers:
                    provider_name = provider.get('provider_name', '')
                    price = provider.get('price', 0)
                    
                    if not price or price <= 0:
                        continue
                    
                    # 清理供应商名称（去掉促销前缀）
                    clean_provider = provider_name
                    # 去掉 [xxx] 格式的前缀
                    if ']' in clean_provider:
                        parts = clean_provider.split(']')
                        clean_provider = parts[-1].strip()
                    # 去掉 "N免邮 " 格式的前缀
                    import re
                    clean_provider = re.sub(r'^\d+免邮\s*', '', clean_provider)
                    
                    source_name = f'药师帮-{clean_provider}' if clean_provider else '药师帮'
                    
                    # 检查是否已存在
                    existing = session.query(PriceRecord).filter(
                        PriceRecord.drug_id == db_drug.id,
                        PriceRecord.source_name == source_name,
                        PriceRecord.price == price
                    ).first()
                    
                    if not existing:
                        price_record = PriceRecord(
                            drug_id=db_drug.id,
                            price=price,
                            source_url='https://dian.ysbang.cn/',
                            source_name=source_name,
                            crawled_at=datetime.utcnow()
                        )
                        session.add(price_record)
                        count += 1
                    else:
                        skipped += 1
            
            # 处理 items 格式（多个药品）
            for item in result.get('items', []):
                item_name = item.get('name', '')
                if not item_name:
                    continue
                
                # 清理药品名称
                clean_name = self._clean_drug_name(item_name)
                
                # 查找或创建药品
                db_drug = session.query(Drug).filter(
                    Drug.name == clean_name
                ).first()
                
                if not db_drug:
                    db_drug = Drug(
                        name=clean_name,
                        specification=item.get('specification', ''),
                        manufacturer=item.get('manufacturer', ''),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(db_drug)
                    session.flush()
                
                # 保存供应商价格
                for provider in item.get('provider_prices', []):
                    provider_name = provider.get('provider_name', '')
                    price = provider.get('price', 0)
                    
                    if not price or price <= 0:
                        continue
                    
                    source_name = f'药师帮-{provider_name}' if provider_name else '药师帮'
                    
                    # 检查是否已存在
                    existing = session.query(PriceRecord).filter(
                        PriceRecord.drug_id == db_drug.id,
                        PriceRecord.source_name == source_name,
                        PriceRecord.price == price
                    ).first()
                    
                    if not existing:
                        price_record = PriceRecord(
                            drug_id=db_drug.id,
                            price=price,
                            source_url='https://dian.ysbang.cn/',
                            source_name=source_name,
                            crawled_at=datetime.utcnow()
                        )
                        session.add(price_record)
                        count += 1
                    else:
                        skipped += 1
            
            session.commit()
            
            if skipped > 0:
                logger.info(f"[Playwright] 保存了 {count} 条新记录，跳过 {skipped} 条已存在记录")
            else:
                logger.info(f"[Playwright] 保存了 {count} 条价格记录")
            
        except Exception as e:
            logger.error(f"[Playwright] 保存数据失败: {e}")
            session.rollback()
        finally:
            session.close()
        
        return count
    
    def crawl_drug_detail_with_playwright(
        self,
        keyword: str,
        drug_id: int = None,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        使用 Playwright 爬取单个药品的所有供应商价格
        
        Args:
            keyword: 药品关键词
            drug_id: 药品ID（可选）
            headless: 是否无头模式
            
        Returns:
            爬取结果
        """
        try:
            from scraper.utils.playwright_crawler import crawl_drug_prices_sync
        except ImportError:
            return {
                'success': False,
                'error': 'Playwright 未安装'
            }
        
        logger.info(f"[Playwright] 爬取药品详情: {keyword}")
        
        token = self._get_cached_token()
        
        result = crawl_drug_prices_sync(
            keyword=keyword,
            token=token,
            headless=headless
        )
        
        return result

    def crawl_all_search_results(
        self,
        keyword: str,
        max_drugs: int = 10,
        max_providers_per_drug: int = 50,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        采集搜索结果中的所有药品及其供应商价格
        
        工作流程:
        1. 搜索关键词，获取所有匹配的药品列表
        2. 对每个药品，采集其所有供应商价格
        3. 保存到数据库
        
        适用场景:
        - 想要获取某个品类的所有药品数据
        - 比如搜索"天麻蜜环菌片"，获取所有品牌/规格的数据
        
        Args:
            keyword: 搜索关键词
            max_drugs: 最多采集多少个药品
            max_providers_per_drug: 每个药品最多采集多少个供应商
            save_to_db: 是否保存到数据库
            
        Returns:
            采集结果
        """
        result = {
            'keyword': keyword,
            'success': False,
            'total_drugs': 0,
            'total_providers': 0,
            'total_saved': 0,
            'drugs': [],
            'error': None
        }
        
        logger.info(f"[批量采集] 开始采集搜索结果: {keyword}")
        
        try:
            # 1. 先用API快速获取搜索结果
            api_result = self.crawl_with_api(keyword)
            
            if not api_result.get('success'):
                # 如果API失败，使用Playwright搜索
                logger.warning("[批量采集] API搜索失败，使用Playwright")
                return self._crawl_search_with_playwright(
                    keyword, max_drugs, max_providers_per_drug, save_to_db
                )
            
            # 2. 从API结果中提取药品列表
            items = api_result.get('items', [])
            logger.info(f"[批量采集] API找到 {len(items)} 个药品")
            
            if not items:
                result['error'] = '未找到任何药品'
                return result
            
            # 3. 限制采集数量
            items_to_crawl = items[:max_drugs]
            logger.info(f"[批量采集] 将采集前 {len(items_to_crawl)} 个药品")
            
            # 4. 逐个采集每个药品的供应商价格
            for idx, item in enumerate(items_to_crawl, 1):
                drug_name = item.get('name', '')
                drug_id = item.get('drug_id')
                
                logger.info(f"[批量采集] ({idx}/{len(items_to_crawl)}) 采集: {drug_name}")
                
                # 使用完整模式采集该药品
                drug_result = self.crawl_complete_mode(
                    keyword=drug_name,
                    drug_id=drug_id,
                    save_to_db=save_to_db
                )
                
                if drug_result.get('success'):
                    providers = drug_result.get('providers', [])
                    saved_count = drug_result.get('saved_count', 0)
                    
                    result['drugs'].append({
                        'name': drug_name,
                        'drug_id': drug_id,
                        'providers_count': len(providers),
                        'saved_count': saved_count,
                        'success': True
                    })
                    
                    result['total_providers'] += len(providers)
                    result['total_saved'] += saved_count
                    
                    logger.info(f"[批量采集] ✅ {drug_name}: {len(providers)}个供应商, 保存{saved_count}条")
                else:
                    result['drugs'].append({
                        'name': drug_name,
                        'drug_id': drug_id,
                        'success': False,
                        'error': drug_result.get('error')
                    })
                    logger.warning(f"[批量采集] ❌ {drug_name}: {drug_result.get('error')}")
            
            result['total_drugs'] = len(result['drugs'])
            result['success'] = True
            
            logger.info(f"[批量采集] 完成! 采集{result['total_drugs']}个药品, {result['total_providers']}个供应商, 保存{result['total_saved']}条记录")
            
        except Exception as e:
            logger.error(f"[批量采集] 异常: {e}")
            result['error'] = str(e)
        
        return result
    
    def _crawl_search_with_playwright(
        self,
        keyword: str,
        max_drugs: int = 10,
        max_providers_per_drug: int = 50,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        使用Playwright采集搜索结果（备用方案）
        
        当API搜索失败时使用
        """
        result = {
            'keyword': keyword,
            'success': False,
            'total_drugs': 0,
            'total_providers': 0,
            'total_saved': 0,
            'drugs': [],
            'error': None
        }
        
        try:
            from scraper.utils.playwright_crawler import crawl_search_results_sync
        except ImportError:
            result['error'] = 'Playwright 未安装'
            return result
        
        logger.info(f"[批量采集-PW] 使用Playwright搜索: {keyword}")
        
        token = self._get_cached_token()
        
        # 使用Playwright搜索
        search_result = crawl_search_results_sync(
            keyword=keyword,
            token=token,
            max_items=max_drugs,
            headless=True
        )
        
        if not search_result.get('success'):
            result['error'] = search_result.get('error', '搜索失败')
            return result
        
        items = search_result.get('items', [])
        logger.info(f"[批量采集-PW] 找到 {len(items)} 个药品")
        
        # 逐个采集
        for idx, item in enumerate(items, 1):
            drug_name = item.get('name', '')
            drug_id = item.get('drug_id')
            
            logger.info(f"[批量采集-PW] ({idx}/{len(items)}) 采集: {drug_name}")
            
            drug_result = self.crawl_complete_mode(
                keyword=drug_name,
                drug_id=drug_id,
                save_to_db=save_to_db
            )
            
            if drug_result.get('success'):
                providers = drug_result.get('providers', [])
                saved_count = drug_result.get('saved_count', 0)
                
                result['drugs'].append({
                    'name': drug_name,
                    'drug_id': drug_id,
                    'providers_count': len(providers),
                    'saved_count': saved_count,
                    'success': True
                })
                
                result['total_providers'] += len(providers)
                result['total_saved'] += saved_count
            else:
                result['drugs'].append({
                    'name': drug_name,
                    'drug_id': drug_id,
                    'success': False,
                    'error': drug_result.get('error')
                })
        
        result['total_drugs'] = len(result['drugs'])
        result['success'] = True
        
        return result
