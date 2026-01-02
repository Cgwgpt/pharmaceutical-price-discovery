# 价格异常标注与商品分类修复

## 问题描述

采集"片仔癀"时，数据库中出现了以下问题：
1. **价格混淆**：化妆品（¥5.99珍珠霜）、1粒装药品（¥650-960）、10粒装药品（¥6863）混在一起
2. **商品类别不清**：药品、化妆品、医疗器械等没有区分
3. **规格混淆**：不同包装规格（1粒 vs 10粒）被归为同一商品

## 解决方案

### 1. 数据库模型增强

#### 新增字段

**drugs 表**：
- `category`: 商品类别（drug/cosmetic/medical_device/health_product）

**price_records 表**：
- `is_outlier`: 价格异常标注
  - 0 = 正常价格
  - 1 = 异常高价
  - -1 = 异常低价
  - 2 = 占位价格（9999等）
- `outlier_reason`: 异常原因说明

### 2. 商品类别自动检测

实现了 `_detect_product_category()` 方法，根据商品名称自动识别类别：

```python
# 化妆品关键词
cosmetic_keywords = ['珍珠霜', '珍珠膏', '面霜', '乳液', '精华', '化妆', '护肤', ...]

# 医疗器械关键词  
device_keywords = ['血糖仪', '血压计', '体温计', '雾化器', '口罩', '手套', ...]

# 保健品关键词
health_keywords = ['维生素', '钙片', '鱼油', '蛋白粉', '益生菌', ...]
```

### 3. 价格异常自动标注

实现了 `_mark_price_outliers()` 方法，使用统计学方法标注异常价格：

**标注规则**：
1. **占位价格检测**：9999, 99999, 999999 等明显的占位价格
2. **IQR离群值检测**：使用四分位距（IQR）方法
   - 计算 Q1（25%分位）和 Q3（75%分位）
   - IQR = Q3 - Q1
   - 异常低价：< Q1 - 1.5 × IQR
   - 异常高价：> Q3 + 1.5 × IQR

### 4. 严格的商品匹配

采集时严格按照 **名称 + 规格 + 厂家** 三要素匹配商品：

```python
db_drug = session.query(Drug).filter(
    Drug.name == clean_name,
    Drug.specification == spec,
    Drug.manufacturer == manufacturer
).first()
```

这样确保：
- "片仔癀3g*1粒" 和 "片仔癀3g*10粒" 是不同商品
- "片仔癀珍珠霜" 和 "片仔癀3g*1粒" 是不同类别

## 实施结果

### 数据库迁移

```bash
python migrate_add_outlier_fields.py
```

结果：
- ✓ 添加 is_outlier 字段
- ✓ 添加 outlier_reason 字段
- ✓ category 字段已存在

### 现有数据更新

```bash
python update_existing_data.py
```

结果：
- ✓ 更新了 9 个非药品商品的类别
  - 3个化妆品（片仔癀珍珠霜/珍珠膏）
  - 1个医疗器械（医用外科口罩）
  - 5个保健品（益生菌、维生素等）
- ✓ 标注了 9 条异常价格

### 片仔癀数据验证

**按类别区分**：
```
化妆品：
- 皇后 片仔癀 珍珠霜 25g: ¥5.99 ~ ¥10.59
- 皇后牌 片仔癀 珍珠膏 20g: ¥34.8

药品：
- 片仔癀 3g*1粒(RX): ¥650 ~ ¥960 (正常价格)
- 片仔癀 3g*10粒: ¥6863.67 ~ ¥6898.33
```

**异常价格标注**（ID=205）：
```
¥9999  - 占位价格 ⚠️
¥960   - 异常高价 (高于 ¥950.00) ⚠️
¥830   - 正常
¥788.5 - 正常
¥788   - 正常
```

## API 变更

### PriceService

**get_drug_prices()**：
```python
# 新增参数
include_outliers: bool = True  # 是否包含异常价格（默认包含但标注）

# 返回值增加字段
{
    'price': 650.0,
    'is_outlier': 0,           # 新增
    'outlier_reason': None     # 新增
}
```

**get_all_drugs_with_stats()**：
```python
# 新增参数
category: str = None  # 按类别筛选: drug, cosmetic, medical_device, health_product

# 返回值增加字段
{
    'name': '片仔癀3g*1粒(RX)',
    'category': 'drug',        # 新增
    'min_price': 650.0,
    'max_price': 960.0
}
```

## 前端显示建议

### 1. 价格列表显示

```html
<div class="price-item">
    <span class="price">¥650.00</span>
    <span class="source">药师帮-吉药庄</span>
    <!-- 正常价格 -->
</div>

<div class="price-item price-outlier">
    <span class="price">¥9999.00</span>
    <span class="source">药师帮-玖药惠</span>
    <span class="badge badge-warning">占位价格</span>
</div>

<div class="price-item price-outlier-high">
    <span class="price">¥960.00</span>
    <span class="source">药师帮-江南医药城</span>
    <span class="badge badge-danger">异常高价</span>
</div>
```

### 2. 商品类别标签

```html
<span class="badge badge-primary">药品</span>
<span class="badge badge-info">化妆品</span>
<span class="badge badge-success">医疗器械</span>
<span class="badge badge-warning">保健品</span>
```

### 3. 价格统计

显示价格范围时，可以提供两种视图：
- **全部价格**：¥650 ~ ¥9999（含异常）
- **正常价格**：¥650 ~ ¥830（仅正常价格）

## 最佳实践

### 采集时

1. **严格区分规格**：确保 API 返回的 specification 字段准确
2. **提取商品类别**：从 API 或商品名称中识别类别
3. **保存完整信息**：名称、规格、厂家三要素完整保存

### 显示时

1. **标注异常价格**：用颜色或图标标识异常价格
2. **提供过滤选项**：允许用户选择是否显示异常价格
3. **类别筛选**：提供按商品类别筛选的功能
4. **规格对比**：同一药品不同规格分开显示

## 总结

通过以下改进，彻底解决了价格混淆问题：

✅ **商品分类清晰**：药品、化妆品、医疗器械、保健品自动识别  
✅ **规格严格区分**：1粒装和10粒装不再混淆  
✅ **异常价格标注**：占位价格、离群值自动标注但不删除  
✅ **数据完整性**：保留所有价格数据，由前端决定如何展示  
✅ **可追溯性**：异常原因记录在数据库中

这样既保证了数据的完整性，又为用户提供了清晰的价格参考。
