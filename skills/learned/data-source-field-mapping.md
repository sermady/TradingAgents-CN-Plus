# -*- coding: utf-8 -*-
"""
数据源字段名映射不匹配问题

处理不同数据源返回字段名不一致导致的N/A问题
"""

## 问题现象

分析报告中财务指标显示为 **N/A**，但数据源实际有数据：

| 报告字段 | 显示值 | 期望 | 数据源字段 |
|---------|--------|------|-----------|
| 营收同比增速 | N/A | +15.5% | `or_yoy` |
| 净利润同比增速 | N/A | +20.3% | `q_profit_yoy` |
| 筹资性现金流净额 | N/A | -0.50亿元 | `n_cashflow_fin_act` |

## 根本原因

不同数据源使用不同的字段命名规范：

```python
# Tushare 返回的字段名
{
    "or_yoy": 15.5,          # 营收同比增速 (Operating Revenue YoY)
    "q_profit_yoy": 20.3,    # 净利润同比增速 (Quarterly Profit YoY)
    "n_cashflow_fin_act": -50000000,  # 筹资性现金流净额
}

# 代码中使用的字段名
{
    "revenue_yoy": None,      # ❌ 找不到对应字段
    "net_income_yoy": None,   # ❌ 找不到对应字段
    "financing_cashflow": None,  # ❌ 找不到对应字段
}
```

## 修复方案

### 1. 多字段名映射支持

```python
# 在 _parse_financial_data_with_stock_info() 中
def _parse_financial_data_with_stock_info(self, financial_data, stock_info, price_value):
    # 🔥 支持多种字段名：Tushare (or_yoy), 通用 (revenue_yoy)
    revenue_yoy = (
        financial_data.get("or_yoy")  # Tushare 字段名 - 第一优先级
        or financial_data.get("revenue_yoy")  # 通用字段名
        or financial_data.get("oper_rev_yoy")
        or (stock_info.get("or_yoy") if stock_info else None)  # 从 stock_info 获取
    )
    
    if revenue_yoy and str(revenue_yoy) not in ["nan", "--", "None", "", "NoneType"]:
        try:
            revenue_yoy_val = float(revenue_yoy)
            metrics["revenue_yoy"] = revenue_yoy_val
            metrics["revenue_yoy_fmt"] = f"{revenue_yoy_val:+.1f}%"
            logger.info(f"✅ 营收同比增速: {revenue_yoy_val:+.1f}%")
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️ 营收同比增速格式错误: {revenue_yoy}, 错误: {e}")
            metrics["revenue_yoy"] = None
            metrics["revenue_yoy_fmt"] = "N/A"
```

### 2. 多重数据源优先级

```python
# 第一优先级：从 financial_data 直接获取
try:
    revenue_yoy_direct = financial_data.get("or_yoy")
    if revenue_yoy_direct and str(revenue_yoy_direct) not in ["nan", "--", "None", "", "NoneType"]:
        revenue_yoy = float(revenue_yoy_direct)
        logger.info(f"✅ 从 Tushare 字段获取营收同比增速: {revenue_yoy:+.1f}%")
except Exception as e:
    logger.debug(f"从 financial_data 获取增速字段失败: {e}")

# 第二优先级：从 stock_info 获取
if revenue_yoy is None:
    revenue_yoy = stock_info.get("or_yoy") if stock_info else None

# 第三优先级：从 income_statement 计算
if revenue_yoy is None and len(income_statement) >= 4:
    revenue_yoy = self._calculate_yoy_from_statements(income_statement)
```

## 常见字段名映射表

### 财务增速字段

| 中文名称 | Tushare 字段 | 通用字段名 | 备用字段 |
|---------|-------------|-----------|---------|
| 营收同比增速 | `or_yoy` | `revenue_yoy` | `oper_rev_yoy` |
| 净利润同比增速 | `q_profit_yoy` | `net_income_yoy` | `n_income_yoy` |
| EPS同比增速 | `eps_yoy` | `eps_growth` | - |
| ROE同比增速 | `roe_yoy` | `roe_growth` | - |

### 现金流字段

| 中文名称 | Tushare 字段 | 字段说明 |
|---------|-------------|---------|
| 经营性现金流净额 | `n_cashflow_act` | Net Cash Flow from Operating Activities |
| 投资性现金流净额 | `n_cashflow_inv_act` | Net Cash Flow from Investing Activities |
| 筹资性现金流净额 | `n_cashflow_fin_act` | Net Cash Flow from Financing Activities |

### 每股指标字段

| 中文名称 | Tushare 字段 | 通用字段名 |
|---------|-------------|-----------|
| 基本每股收益 | `diluted2_eps` | `eps` |
| 每股净资产 | `bps` | `book_value_per_share` |
| 每股经营现金流 | `ocfps` | `operating_cash_flow_per_share` |

## 最佳实践

### 1. 添加字段名检查

```python
def validate_field_names(data: dict, expected_fields: list) -> dict:
    """验证字段名是否存在，并返回映射关系"""
    mapping = {}
    for expected in expected_fields:
        # 尝试多种可能的字段名
        for variant in get_field_variants(expected):
            if variant in data:
                mapping[expected] = variant
                break
        else:
            logger.warning(f"未找到字段 {expected} 的任何变体")
    return mapping

def get_field_variants(field_name: str) -> list:
    """获取字段名的所有可能变体"""
    variants_map = {
        "revenue_yoy": ["or_yoy", "revenue_yoy", "oper_rev_yoy", "revenue_growth"],
        "net_income_yoy": ["q_profit_yoy", "net_income_yoy", "n_income_yoy", "profit_growth"],
        "eps": ["diluted2_eps", "eps", "basic_eps", "earnings_per_share"],
        # ... 更多映射
    }
    return variants_map.get(field_name, [field_name])
```

### 2. 日志记录字段映射

```python
# 记录实际使用的字段名
logger.info(f"📊 字段映射: or_yoy={financial_data.get('or_yoy')}, "
            f"q_profit_yoy={financial_data.get('q_profit_yoy')}")
```

### 3. 单元测试覆盖

```python
def test_yoy_field_parsing():
    """测试增速字段解析"""
    provider = OptimizedChinaDataProvider()
    
    # 测试 Tushare 字段名
    financial_data = {
        "or_yoy": 15.5,
        "q_profit_yoy": 20.3,
    }
    metrics = provider._parse_financial_data_with_stock_info(
        financial_data, {}, 10.0
    )
    assert metrics.get('revenue_yoy_fmt') == "+15.5%"
    assert metrics.get('net_income_yoy_fmt') == "+20.3%"
    
    # 测试备选字段名
    financial_data = {
        "revenue_yoy": 16.5,
        "net_income_yoy": 22.3,
    }
    metrics = provider._parse_financial_data_with_stock_info(
        financial_data, {}, 10.0
    )
    assert metrics.get('revenue_yoy_fmt') == "+16.5%"
    assert metrics.get('net_income_yoy_fmt') == "+22.3%"
```

## 调试技巧

### 检查实际返回的字段名

```python
# 在 Tushare 适配器中打印原始字段
print("Tushare 返回的字段:", df.columns.tolist())
print("样本数据:", df.iloc[0].to_dict())
```

### 验证字段映射

```python
# 检查 financial_data 中是否有增速字段
print("or_yoy in financial_data:", "or_yoy" in financial_data)
print("q_profit_yoy in financial_data:", "q_profit_yoy" in financial_data)
print("stock_info or_yoy:", stock_info.get("or_yoy") if stock_info else None)
```

## 何时使用

**触发条件**:
- 报告中出现 N/A 但数据源应该有值
- 添加新的数据源适配器
- 数据源 API 升级导致字段名变化
- 多数据源混用时字段名不一致

**检查清单**:
- [ ] 确认数据源的原始字段名
- [ ] 添加所有可能的字段名变体
- [ ] 设置正确的优先级顺序
- [ ] 添加详细的日志记录
- [ ] 编写单元测试验证映射逻辑
