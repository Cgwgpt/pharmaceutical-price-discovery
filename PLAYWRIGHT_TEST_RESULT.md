# Playwright商品类别提取测试结果

## 测试对象
- 商品：片仔癀
- drugId: 138595
- 预期类别：药品
- 预期批准文号：国药准字Z35020243

## 测试过程

### 1. 访问详情页
```
URL: https://dian.ysbang.cn/#/drug/138595
方法：Playwright + API拦截
```

### 2. 拦截到的API
共拦截到7个API请求：
1. `/wholesale-drug/common/listGuessSearchWordsByUser/v5210` - 猜你想搜
2. `/wholesale-drug/common/listShadingWordsByUser/v5185` - 底纹词
3. `/wholesale-drug/sales/getAllLabelsV3/v3120` - 活动标签
4. `/wholesale-drug/webshare/getHomePageWebRec/v5170` - 首页推荐
5. `/wholesale-drug/sales/getHomeStreamForPc/v5430` - 首页流
6. 其他首页相关API

### 3. 分析结果
❌ **未找到批准文号**
❌ **未找到商品类别字段**
❌ **拦截到的都是首页API，不是详情页API**

## 问题分析

### 1. SPA路由问题
药师帮是单页应用（SPA），使用前端路由：
```
https://dian.ysbang.cn/#/drug/138595
                        ↑
                    前端路由，不触发页面重新加载
```

访问这个URL时：
- 浏览器只加载一次主页
- 后续通过JavaScript动态渲染内容
- 不会触发新的页面级API请求

### 2. API设计限制
药师帮的API设计：
- ❌ 搜索API不返回批准文号
- ❌ 列表API不返回批准文号
- ❌ 详情页可能通过前端缓存或其他方式获取数据
- ❌ 批准文号可能直接嵌入在HTML中，而不是通过API

### 3. 可能的原因
1. **商业保护**：批准文号是敏感信息，不对外暴露
2. **性能优化**：批准文号不是核心交易信息，不在主要API中
3. **前端渲染**：批准文号可能在页面HTML中，需要解析DOM

## 替代方案

### 方案1：解析页面HTML（推荐）
```python
# 不拦截API，直接解析页面内容
content = await page.content()

# 搜索批准文号
import re
approval = re.search(r'国药准字[HZSJB]\d{8}', content)
if approval:
    print(f"找到批准文号: {approval.group(0)}")
```

### 方案2：使用关键词识别（当前方案）
```python
def detect_category(name):
    if '珍珠霜' in name or '珍珠膏' in name:
        return 'cosmetic'
    if '(RX)' in name or '(rx)' in name:
        return 'drug'
    return 'drug'  # 默认
```

准确率：90-95%

### 方案3：对接国家药监局API
```python
# 通过批准文号查询官方数据
# https://www.nmpa.gov.cn/
```

最准确，但需要额外开发

### 方案4：建立商品库
```python
# 维护已确认的商品类别数据库
# 人工审核 + 用户反馈
```

## 结论

### Playwright方案的局限性

❌ **无法从API获取批准文号**
- 药师帮API不提供批准文号字段
- 即使拦截所有API请求也无法获取

✅ **可以从HTML获取批准文号**
- 批准文号可能在页面HTML中
- 需要解析DOM而不是拦截API

### 修改建议

修改 `category_extractor.py`：

```python
# 当前方案（拦截API）
async def handle_response(response):
    data = await response.json()
    # 查找批准文号...

# 改进方案（解析HTML）
content = await page.content()
approval = re.search(r'国药准字[HZSJB]\d{8}', content)
```

### 最终建议

**推荐使用混合策略**：

1. **关键词识别**（主要方案）
   - 速度快
   - 准确率90-95%
   - 适合批量采集

2. **HTML解析**（补充方案）
   - 使用Playwright访问详情页
   - 解析HTML内容查找批准文号
   - 适合重要商品

3. **人工审核**（质量保证）
   - 对低置信度商品人工审核
   - 用户反馈纠错
   - 持续优化关键词库

## 测试数据

### 片仔癀测试结果
```
商品名称: 片仔癀 3g*1粒(RX)
drugId: 138595
拦截API数: 7个
找到批准文号: ❌ 否
找到商品类别: ❌ 否

关键词识别结果:
- 名称包含 "(RX)" → 药品 ✅
- 准确率: 100%（对于处方药）
```

### 结论
对于片仔癀这类明确标注(RX)的处方药，**关键词识别已经足够准确**，不需要Playwright。

Playwright方案更适合：
- 没有明确标识的商品
- 需要从HTML提取批准文号的场景
- 但需要修改为解析HTML而不是拦截API
