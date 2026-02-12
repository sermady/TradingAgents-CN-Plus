# -*- coding: utf-8 -*-
"""
TTM指标使用规范与PE/PS区分说明

明确区分和使用TTM（滚动十二个月）指标与静态指标
"""

## 问题背景

**TTM (Trailing Twelve Months)** 是财务分析中重要的滚动指标，与静态指标有本质区别。

### 常见混淆

| 指标类型 | 计算方法 | 特点 | 用途 |
|---------|---------|------|------|
| **PE_TTM** | 总市值 / TTM净利润 | 反映最近12个月盈利能力 | 市场主流估值指标 |
| **PE静态** | 总市值 / 年报净利润 | 基于完整财年数据 | 年度对比分析 |
| **PS_TTM** | 总市值 / TTM营业收入 | 反映最近12个月营收水平 | 估值分析优先 |
| **PS静态** | 总市值 / 单期营业收入 | 可能受季节性影响 | 季度对比参考 |

## 关键区别示例

### PE_TTM vs PE静态

```
假设：
- 总市值 = 268.81亿元
- PE_TTM = 25.7倍（数据源提供）
- 年报归母净利润 = 7.60亿元
- TTM净利润 = 10.46亿元（从PE_TTM反推：268.81÷25.7）

计算验证：
✓ PE_TTM = 268.81 ÷ 10.46 = 25.7倍（与数据源一致）
✗ 错误：268.81 ÷ 7.60 = 35.4倍（这是PE静态，不是PE_TTM）

差异原因：10.46亿(TTM) vs 7.60亿(年报) = 利润口径不同！
```

### PS_TTM vs PS静态

```
假设：
- 总市值 = 268.81亿元
- PS_TTM = 2.5倍（基于TTM营收107.5亿元）
- PS静态 = 3.33倍（基于年度营收80.72亿元）

计算验证：
✓ PS_TTM = 268.81 ÷ 107.5 = 2.5倍（反映最近12个月营收能力）
✗ PS静态 = 268.81 ÷ 80.72 = 3.33倍（仅反映单期营收）

差异原因：TTM营收（107.5亿）vs 年度营收（80.72亿）= 营收口径不同！
```

## 使用规范

### 1. 估值分析强制使用TTM指标

```python
# ✅ 正确做法
valuation_analysis = {
    "pe_ttm": data["pe_ttm"],  # 必须使用TTM
    "ps_ttm": data["ps_ttm"],  # 必须使用TTM
}

# ❌ 错误做法
valuation_analysis = {
    "pe": data["pe"],  # 错误：可能使用静态PE
    "ps": data["ps"],  # 错误：使用静态PS
}
```

### 2. 分析师提示词要求

**fundamentals_analyst.py 中的强制要求**:

```markdown
🔴 【强制要求】估值指标使用规范：

**必须使用TTM指标（滚动指标）**：
- **PE_TTM（滚动市盈率）**：数据源提供，基于TTM净利润计算
  - ✅ **强制**：估值分析时必须优先使用 PE_TTM，而不是 PE静态
  - ✅ **验算**：使用公式 总市值 ÷ TTM净利润 = PE_TTM 进行验证
  - ❌ **禁止**：仅使用 PE静态进行估值判断

- **PS_TTM（滚动市销率）**：数据源提供，基于TTM营业收入计算
  - ✅ **强制**：如数据可用，估值分析时必须优先使用 PS_TTM，而不是 PS静态
  - ✅ **验算**：使用公式 总市值 ÷ TTM营业收入 = PS_TTM 进行验证
```

### 3. 报告撰写格式

```markdown
#### 市盈率（PE）指标：
- **PE_TTM：25.7倍** ✅ **【估值分析使用此指标】**
  - 基于：TTM净利润10.46亿元，总市值268.81亿元
  - 验算：268.81 ÷ 10.46 = 25.7倍 ✓
  - 数据来源：Tushare官方计算
- PE静态：35.4倍（仅作参考，基于年报净利润7.60亿元）
  - 说明：PE_TTM（25.7倍）与PE静态（35.4倍）差异37.7%

#### 市销率（PS）指标：
- **PS_TTM：2.5倍** ✅ **【估值分析使用此指标】**
  - 基于：TTM营业收入107.5亿元，总市值268.81亿元
  - 验算：268.81 ÷ 107.5 = 2.5倍 ✓
- PS（静态）：3.33倍（仅作参考，基于年度营收80.72亿元）
```

## 数据源字段

### Tushare daily_basic 接口

```python
fields = (
    "ts_code,total_mv,circ_mv,pe,pb,ps,"
    "pe_ttm,pb_mrq,ps_ttm,"  # TTM指标
    "dv_ratio,dv_ttm,"       # 股息率
    "total_share,float_share"  # 股本
)
```

### 字段获取代码

```python
# tushare.py
basic_data["pe_ttm"] = row["pe_ttm"]
basic_data["ps_ttm"] = row.get("ps_ttm")
basic_data["dv_ratio"] = row.get("dv_ratio")
basic_data["dv_ttm"] = row.get("dv_ttm")
```

## 常见错误

### 错误1：用静态指标估值

```markdown
❌ 错误示例：
- 市盈率：35.4倍（仅提供PE静态，未说明PE_TTM）
- 市销率：3.33倍（仅提供PS静态，未使用PS_TTM）
- 估值判断：基于PE 35.4倍...[使用静态指标进行判断，错误！]
```

### 错误2：验算时使用错误口径

```python
# ❌ 错误：用年报净利润验算PE_TTM
pe_calculated = market_cap / annual_profit  # 35.4倍，错误！

# ✅ 正确：用TTM净利润验算PE_TTM
ttm_profit = market_cap / pe_ttm  # 反推TTM净利润
pe_calculated = market_cap / ttm_profit  # 25.7倍，正确！
```

### 错误3：字段获取不完整

```python
# ❌ 错误：_get_valuation_indicators 遗漏字段
return {
    "pe": result.get("pe"),
    "pb": result.get("pb"),
    # ❌ 缺少 ps_ttm, dv_ttm 等
}

# ✅ 正确：完整返回所有字段
return {
    "pe": result.get("pe"),
    "pb": result.get("pb"),
    "pe_ttm": result.get("pe_ttm"),
    "ps": result.get("ps"),
    "ps_ttm": result.get("ps_ttm"),  # ✅
    "dv_ratio": result.get("dv_ratio"),  # ✅
    "dv_ttm": result.get("dv_ttm"),  # ✅
}
```

## 检查清单

在分析师提示词中添加：

```markdown
⚠️ **【强制要求】估值指标使用检查清单**：
- [ ] 报告中明确列出 PE_TTM 数值，并标注"【估值分析使用此指标】"
- [ ] 报告中明确列出 PS_TTM 数值（如可用），并标注"【估值分析使用此指标】"
- [ ] 估值判断、目标价计算、投资建议均基于TTM指标
- [ ] 如PE_TTM或PS_TTM数据缺失，明确说明并解释原因
- [ ] 禁止仅使用静态指标（PE静态、PS静态）进行估值判断
- [ ] 验算时使用TTM口径数据（TTM净利润、TTM营业收入）
⚠️ **违反以上任何一条，报告将被视为不合格**。
```

## 相关技能

- [数据源字段名映射不匹配问题](data-source-field-mapping.md)
- [数据单位与财务计算规范](data-unit-standards.md)
- [数据质量检查模式](data-quality-checks.md)

## 参考文档

- Tushare官方文档：[每日指标接口 daily_basic](https://tushare.pro/document/2?doc_id=32)
- 同花顺/东方财富：显示的PE/PS均为TTM值
