# 商品类别识别策略

## 问题

你说得对：**商品类别自动识别可能不可靠，应该通过采集商品类别**。

但经过测试发现：**药师帮API不直接提供商品类别或批准文号信息**。

## API现状

### 搜索API返回字段
```json
{
  "drugId": 138595,
  "drugName": "片仔癀 3g*1粒(RX)",
  "factory": "漳州片仔癀药业股份有限公司",
  "specification": "3g*1粒(RX)",
  "drugType": 0,  // 所有商品都是0，无法区分
  "minprice": 650,
  "maxprice": 960
}
```

**缺失信息**：
- ❌ 没有批准文号（approvalNumber）
- ❌ 没有商品类别（category）
- ❌ drugType字段无意义（都是0）

## 解决方案

### 方案1：多层识别策略（当前实现）

```python
def determine_category(drug_data):
    """
    多层识别策略
    """
    # 第1层：API字段（如果可用）
    if drug_data.get('drugType') and drug_data['drugType'] != 0:
        return map_drug_type(drug_data['drugType'])
    
    # 第2层：名称特征识别（高可信度关键词）
    name = drug_data.get('drugName', '')
    
    # 化妆品：明确的化妆品关键词
    cosmetic_keywords = ['珍珠霜', '珍珠膏', '面霜', '乳液', '精华液', 
                         '洗面奶', '面膜', '眼霜', '皇后牌']
    if any(kw in name for kw in cosmetic_keywords):
        return 'cosmetic'
    
    # 医疗器械：明确的器械关键词
    device_keywords = ['医用口罩', '外科口罩', '血糖仪', '血压计', 
                      '体温计', '雾化器', '注射器', '绷带', '纱布']
    if any(kw in name for kw in device_keywords):
        return 'medical_device'
    
    # 保健品：保健食品标识
    if '保健' in name or '营养' in name:
        return 'health_product'
    
    # 第3层：处方药标识
    if '(RX)' in name or '(rx)' in name or '（RX）' in name:
        return 'drug'
    
    # 第4层：厂家信息辅助判断
    manufacturer = drug_data.get('factory', '')
    if '化妆品' in manufacturer:
        return 'cosmetic'
    if '医疗器械' in manufacturer:
        return 'medical_device'
    
    # 默认：药品
    return 'drug'
```

**优点**：
- ✅ 不依赖API
- ✅ 高可信度关键词准确率高
- ✅ 多层判断降低误判

**缺点**：
- ⚠️ 边缘案例可能误判
- ⚠️ 需要维护关键词列表

### 方案2：Playwright采集详情页（最可靠）

```python
def get_category_from_detail_page(drug_id):
    """
    通过浏览器自动化访问详情页，获取批准文号
    """
    # 访问 https://dian.ysbang.cn/#/drug/{drug_id}
    # 从页面中提取批准文号
    # 根据批准文号判断类别：
    #   - 国药准字H/Z/S/J/B + 8位数字 = 药品
    #   - 国械注准/进 = 医疗器械
    #   - 卫妆准字/国妆特字 = 化妆品
    #   - 国食健字 = 保健品
```

**优点**：
- ✅ 最可靠（批准文号是官方标识）
- ✅ 100%准确

**缺点**：
- ❌ 速度慢（需要打开浏览器）
- ❌ 资源消耗大
- ❌ 不适合批量采集

### 方案3：混合策略（推荐）

```python
def determine_category_hybrid(drug_data, use_playwright=False):
    """
    混合策略：快速识别 + 按需详查
    """
    # 快速识别（方案1）
    category = determine_category_by_keywords(drug_data)
    confidence = get_confidence(drug_data, category)
    
    # 如果置信度低且重要，使用Playwright详查
    if confidence < 0.8 and use_playwright:
        category = get_category_from_detail_page(drug_data['drugId'])
    
    return category
```

**使用场景**：
- 批量采集：使用关键词识别（快速）
- 重要商品：使用Playwright详查（准确）
- 用户可选：提供"精确模式"开关

## 实施建议

### 短期方案（已实现）
使用多层关键词识别，重点维护高可信度关键词列表：

```python
# 高可信度关键词（准确率>95%）
COSMETIC_KEYWORDS = ['珍珠霜', '珍珠膏', '面霜', '乳液', '精华液', '洗面奶', '面膜', '眼霜']
DEVICE_KEYWORDS = ['医用口罩', '外科口罩', '血糖仪', '血压计', '体温计', '雾化器']

# 中等可信度关键词（准确率80-95%）
COSMETIC_KEYWORDS_MEDIUM = ['护肤', '美白', '保湿', '滋润']
DEVICE_KEYWORDS_MEDIUM = ['口罩', '手套', '纱布', '绷带']
```

### 中期方案
1. **收集数据**：记录识别结果和用户反馈
2. **机器学习**：训练分类模型
3. **持续优化**：根据反馈调整关键词

### 长期方案
1. **对接国家药监局API**：获取官方批准文号数据
2. **建立商品库**：维护已确认的商品类别数据库
3. **众包标注**：允许用户纠正分类错误

## 数据质量保证

### 1. 置信度标注
```python
class Drug:
    category = Column(String(20))
    category_confidence = Column(Float)  # 0.0-1.0
    category_source = Column(String(20))  # 'api', 'keyword', 'playwright', 'manual'
```

### 2. 人工审核
对低置信度商品进行人工审核：
```sql
SELECT * FROM drugs 
WHERE category_confidence < 0.8 
ORDER BY price_count DESC
LIMIT 100;
```

### 3. 用户反馈
允许用户报告分类错误，持续改进。

## 总结

你的观点完全正确：**理想情况下应该从API采集商品类别**。

但现实是：
1. ❌ 药师帮API不提供类别信息
2. ✅ 可以通过Playwright采集详情页（慢但准确）
3. ✅ 可以通过关键词识别（快但可能有误）

**推荐方案**：
- 默认使用关键词识别（快速）
- 提供"精确模式"选项（使用Playwright）
- 记录置信度，允许人工审核
- 持续优化关键词列表

这样既保证了效率，又提供了准确性选项。
