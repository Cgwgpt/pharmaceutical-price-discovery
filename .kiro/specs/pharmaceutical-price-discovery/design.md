# 设计文档

## 概述

医药价格发现系统采用渐进式架构设计，从单体应用开始，逐步演进为模块化系统。技术栈选择以Python生态为主，确保易于学习和快速开发。

### 技术栈选择

| 组件 | 技术选型 | 选择理由 |
|------|----------|----------|
| 爬虫框架 | Scrapy | 成熟稳定，文档丰富，社区活跃 |
| Web框架 | Flask | 轻量级，易于上手，适合快速原型 |
| 数据库 | SQLite → PostgreSQL | 从简单开始，可平滑升级 |
| ORM | SQLAlchemy | Python标准ORM，支持多种数据库 |
| 前端 | Jinja2 + Bootstrap | 服务端渲染，无需前端构建工具 |

## 架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    医药价格发现系统                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Web界面    │  │  爬虫引擎   │  │   价格比较器        │  │
│  │  (Flask)    │  │  (Scrapy)   │  │   (比价逻辑)        │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          │                                   │
│                   ┌──────▼──────┐                            │
│                   │  数据访问层  │                            │
│                   │ (SQLAlchemy) │                            │
│                   └──────┬──────┘                            │
│                          │                                   │
│                   ┌──────▼──────┐                            │
│                   │   数据库    │                            │
│                   │  (SQLite)   │                            │
│                   └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### 目录结构

```
pharma-price-discovery/
├── app/
│   ├── __init__.py          # Flask应用初始化
│   ├── models.py            # 数据模型定义
│   ├── routes.py            # Web路由
│   ├── services/
│   │   ├── __init__.py
│   │   ├── price_service.py # 价格查询服务
│   │   └── compare_service.py # 比价服务
│   └── templates/           # HTML模板
│       ├── base.html
│       ├── index.html
│       └── search.html
├── scraper/
│   ├── __init__.py
│   ├── spiders/
│   │   ├── __init__.py
│   │   └── base_spider.py   # 基础爬虫类
│   ├── items.py             # 数据项定义
│   ├── pipelines.py         # 数据处理管道
│   └── settings.py          # Scrapy配置
├── config.py                # 应用配置
├── requirements.txt         # 依赖列表
└── run.py                   # 启动入口
```

## 组件和接口

### 1. 数据模型层 (models.py)

```python
class Drug:
    """药品基础信息"""
    id: int                  # 主键
    name: str                # 药品名称
    standard_name: str       # 标准化名称
    specification: str       # 规格（如：10mg*24片）
    dosage_form: str         # 剂型（如：片剂、胶囊）
    manufacturer: str        # 生产厂家
    created_at: datetime     # 创建时间

class PriceRecord:
    """价格记录"""
    id: int                  # 主键
    drug_id: int             # 关联药品ID
    price: Decimal           # 价格
    source_url: str          # 来源URL
    source_name: str         # 来源网站名称
    crawled_at: datetime     # 爬取时间

class PriceComparison:
    """价格比较结果（非持久化）"""
    drug_name: str           # 药品名称
    prices: List[PriceInfo]  # 各平台价格列表
    lowest_price: Decimal    # 最低价
    highest_price: Decimal   # 最高价
    price_diff_percent: float # 价差百分比
```

### 2. 爬虫组件 (scraper/)

```python
class DrugItem:
    """爬虫数据项"""
    name: str                # 药品名称
    specification: str       # 规格
    price: str               # 价格（字符串，需清洗）
    source_url: str          # 来源URL
    source_name: str         # 来源网站

class BaseDrugSpider:
    """基础爬虫类"""
    name: str                # 爬虫名称
    allowed_domains: List[str]  # 允许的域名
    start_urls: List[str]    # 起始URL
    
    def parse(response) -> Iterator[DrugItem]:
        """解析页面，提取药品信息"""
        pass

class DrugPipeline:
    """数据处理管道"""
    def process_item(item: DrugItem) -> DrugItem:
        """清洗和标准化数据"""
        pass
    
    def save_to_database(item: DrugItem) -> None:
        """保存到数据库"""
        pass
```

### 3. 服务层接口

```python
class PriceService:
    """价格查询服务"""
    def get_latest_prices(drug_name: str) -> List[PriceRecord]:
        """获取药品最新价格"""
        pass
    
    def get_price_history(drug_id: int, days: int = 30) -> List[PriceRecord]:
        """获取价格历史"""
        pass
    
    def search_drugs(keyword: str) -> List[Drug]:
        """搜索药品"""
        pass

class CompareService:
    """比价服务"""
    def compare_prices(drug_name: str) -> PriceComparison:
        """比较同一药品在不同平台的价格"""
        pass
    
    def find_best_price(drug_name: str) -> PriceRecord:
        """找到最低价格"""
        pass
    
    def calculate_savings(drug_name: str, quantity: int) -> Decimal:
        """计算潜在节省金额"""
        pass
```

### 4. Web路由接口

| 路由 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 首页，显示最近价格 |
| `/search` | GET | 搜索药品 |
| `/drug/<id>` | GET | 药品详情页 |
| `/compare` | GET | 比价结果页 |
| `/api/prices` | GET | 价格数据API |
| `/api/compare` | GET | 比价API |

## 数据模型

### 数据库Schema

```sql
-- 药品表
CREATE TABLE drugs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    standard_name VARCHAR(200),
    specification VARCHAR(100),
    dosage_form VARCHAR(50),
    manufacturer VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 价格记录表
CREATE TABLE price_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (drug_id) REFERENCES drugs(id)
);

-- 药品名称别名表（用于标准化）
CREATE TABLE drug_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_id INTEGER NOT NULL,
    alias_name VARCHAR(200) NOT NULL,
    FOREIGN KEY (drug_id) REFERENCES drugs(id)
);

-- 索引
CREATE INDEX idx_drugs_name ON drugs(name);
CREATE INDEX idx_drugs_standard_name ON drugs(standard_name);
CREATE INDEX idx_price_records_drug_id ON price_records(drug_id);
CREATE INDEX idx_price_records_crawled_at ON price_records(crawled_at);
CREATE INDEX idx_drug_aliases_alias ON drug_aliases(alias_name);
```

### 数据流程

```
网页 → 爬虫解析 → DrugItem → Pipeline清洗 → 数据库存储
                                    ↓
                              标准化处理
                              - 去除空格
                              - 统一单位
                              - 价格转换
```


## 正确性属性

*正确性属性是指在系统所有有效执行中都应保持为真的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性作为人类可读规范和机器可验证正确性保证之间的桥梁。*

### Property 1: 数据提取完整性

*对于任意*有效的药品网页内容，爬虫提取的DrugItem应当包含非空的name、price、source_url和source_name字段。

**验证: 需求 1.2, 2.1**

### Property 2: 数据存储往返一致性

*对于任意*有效的DrugItem，保存到数据库后再查询，应当能够获取到相同的药品名称、价格和来源信息。

**验证: 需求 1.3, 2.2**

### Property 3: 历史记录累积性

*对于任意*药品，多次存储不同价格后，价格记录数量应当等于存储次数，历史记录不会被覆盖。

**验证: 需求 2.2**

### Property 4: 模糊搜索包含性

*对于任意*药品名称的子串作为搜索词，搜索结果中的每个药品名称都应当包含该搜索词。

**验证: 需求 2.3, 3.2**

### Property 5: 比价结果排序正确性

*对于任意*比价结果列表，价格应当按升序排列，即对于列表中任意相邻的两个价格，前一个价格应当小于或等于后一个价格。

**验证: 需求 5.2**

### Property 6: 最低价格标识正确性

*对于任意*比价结果，标记为最低价的价格应当小于或等于结果中的所有其他价格。

**验证: 需求 5.3, 8.1**

### Property 7: 价差百分比计算正确性

*对于任意*比价结果，价差百分比应当等于 (最高价 - 最低价) / 最低价 * 100。

**验证: 需求 5.5**

### Property 8: 数据标准化一致性

*对于任意*输入的药品名称，标准化处理后应当：去除首尾空格、将多个连续空格替换为单个空格、移除特殊字符。

**验证: 需求 6.1**

### Property 9: 规格单位标准化

*对于任意*包含单位的规格字符串，标准化后应当使用统一的单位格式（mg、g、ml、L）。

**验证: 需求 6.3**

### Property 10: 药品标识唯一性

*对于任意*两个标准化后名称相同的药品，应当生成相同的药品标识符。

**验证: 需求 6.4**

### Property 11: 价格变动阈值检测

*对于任意*价格变动，当变动百分比超过设定阈值时，系统应当正确标记为"采购机会"（下降）或"预警"（上涨）。

**验证: 需求 7.2, 7.3**

### Property 12: 成本节省计算正确性

*对于任意*药品和采购数量，潜在节省金额应当等于 (当前采购价 - 最低价) * 数量。

**验证: 需求 8.3**

### Property 13: 爬虫容错性

*对于任意*包含部分无效URL的爬取任务，系统应当成功爬取所有有效URL的数据，无效URL的失败不影响其他URL的处理。

**验证: 需求 1.4, 4.4**


## 错误处理

### 爬虫层错误处理

| 错误类型 | 处理策略 |
|----------|----------|
| 网络超时 | 重试3次，间隔递增（1s, 2s, 4s） |
| HTTP 4xx | 记录日志，跳过该URL |
| HTTP 5xx | 重试2次，失败后跳过 |
| 解析失败 | 记录原始HTML，跳过该页面 |
| 反爬虫检测 | 切换User-Agent，降低请求频率 |

### 数据层错误处理

| 错误类型 | 处理策略 |
|----------|----------|
| 数据库连接失败 | 重试连接，失败后抛出异常 |
| 数据验证失败 | 记录无效数据，跳过存储 |
| 重复数据 | 允许重复（保留历史记录） |

### Web层错误处理

| 错误类型 | 处理策略 |
|----------|----------|
| 404 Not Found | 显示友好的"未找到"页面 |
| 500 Server Error | 显示错误页面，记录详细日志 |
| 搜索无结果 | 显示"未找到匹配药品"提示 |

## 测试策略

### 单元测试

- 使用 pytest 作为测试框架
- 测试覆盖率目标：核心业务逻辑 > 80%
- 重点测试：
  - 数据清洗和标准化函数
  - 价格计算和比较逻辑
  - 数据库CRUD操作

### 属性测试

- 使用 Hypothesis 作为属性测试框架
- 每个属性测试运行至少100次迭代
- 重点验证：
  - 数据标准化的幂等性
  - 价格排序的正确性
  - 计算结果的准确性

### 集成测试

- 测试爬虫到数据库的完整流程
- 测试Web接口的端到端功能
- 使用测试数据库隔离测试环境

### 测试文件结构

```
tests/
├── __init__.py
├── conftest.py              # pytest配置和fixtures
├── test_models.py           # 数据模型测试
├── test_services.py         # 服务层测试
├── test_scraper.py          # 爬虫测试
├── test_properties.py       # 属性测试
└── test_routes.py           # Web路由测试
```

### 属性测试标注格式

每个属性测试必须包含以下注释：

```python
# Feature: pharmaceutical-price-discovery
# Property N: [属性标题]
# Validates: Requirements X.Y
```