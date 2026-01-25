# -*- coding: utf-8 -*-
"""
统一股票数据 Schema 架构设计

## 概述

本模块定义了两种不同类型的股票数据 Schema，分别服务于技术分析和基本面分析：

1. **StockBasicData** - 基础信息 Schema（基本面分析）
2. **StockHistoricalData** - 历史数据 Schema（技术分析）

## 数据流架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          数据获取层                                  │
├─────────────────────────────────────────────────────────────────────┤
│  技术分析师 (Market Analyst)                                         │
│  └── get_stock_market_data_unified()                                │
│      └── 返回: 格式化的字符串报告（含历史日线）                       │
│                                                                      │
│  基本面分析师 (Fundamentals Analyst)                                  │
│  └── get_stock_fundamentals_unified()                               │
│      └── get_stock_info() → standardize_stock_basic() → StockBasicData │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          Schema 层                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────┐    ┌────────────────────────────────────┐  │
│  │   StockBasicData   │    │        StockHistoricalData         │  │
│  │   (基本面分析)      │    │        (技术分析)                  │  │
│  ├────────────────────┤    ├────────────────────────────────────┤  │
│  │ code, name         │    │ code, name, market, currency       │  │
│  │ industry, area     │    │ start_date, end_date               │  │
│  │ pe, pb, ps         │    │ daily_data: List[StockDailyData]   │  │
│  │ total_mv, circ_mv  │    │ latest_ma5/10/20/60                │  │
│  │ turnover_rate      │    │ latest_macd, rsi, boll             │  │
│  └────────────────────┘    └────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## StockBasicData 字段说明（基本面分析）

| 字段组 | 字段名 | 类型 | 说明 |
|--------|--------|------|------|
| **基础信息** | code | str | 股票代码（6位） |
| | name | str | 股票名称 |
| | symbol | str | 交易代码 |
| | ts_code | str | Tushare格式代码 |
| | full_symbol | str | 完整代码（如600765.SH） |
| **市场信息** | market | str | 市场类型（CN/HK/US） |
| | exchange | str | 交易所（上交所/深交所） |
| | list_status | str | 上市状态（L/D/P） |
| **业务信息** | area | str | 所属地区 |
| | industry | str | 所属行业 |
| | industry_sw | str | 申万行业分类 |
| | industry_gn | str | 概念行业分类 |
| **上市信息** | list_date | str | 上市日期 |
| | delist_date | str | 退市日期 |
| | is_hs | str | 是否沪深港通（N/H/S） |
| **财务指标** | pe | float | 市盈率 |
| | pe_ttm | float | 市盈率TTM |
| | pb | float | 市净率 |
| | ps | float | 市销率 |
| | pcf | float | 市现率 |
| | total_mv | float | 总市值（万元） |
| | circ_mv | float | 流通市值（万元） |
| **交易指标** | turnover_rate | float | 换手率（%） |
| | volume_ratio | float | 量比 |

## StockDailyData 字段说明（技术分析 - 单日）

| 字段组 | 字段名 | 类型 | 说明 |
|--------|--------|------|------|
| **基础信息** | ts_code | str | Tushare格式代码 |
| | trade_date | str | 交易日期 |
| **OHLCV** | open | float | 开盘价 |
| | high | float | 最高价 |
| | low | float | 最低价 |
| | close | float | 收盘价 |
| | volume | float | 成交量（股） |
| | amount | float | 成交额（元） |
| **涨跌数据** | change | float | 涨跌额 |
| | pct_chg | float | 涨跌幅（%） |
| **均线** | ma5 | float | 5日均线 |
| | ma10 | float | 10日均线 |
| | ma20 | float | 20日均线 |
| | ma60 | float | 60日均线 |
| **MACD** | macd_dif | float | DIF值 |
| | macd_dea | float | DEA值 |
| | macd_hist | float | MACD柱状图 |
| **RSI** | rsi6 | float | RSI6 |
| | rsi12 | float | RSI12 |
| | rsi24 | float | RSI24 |
| **布林带** | boll_upper | float | 上轨 |
| | boll_middle | float | 中轨 |
| | boll_lower | float | 下轨 |

## 使用示例

### 基本面分析数据获取

```python
from tradingagents.dataflows.schemas import StockBasicData
from tradingagents.dataflows.standardizers import standardize_stock_basic

# 从API获取原始数据
raw_data = api.stock_basic(ts_code='600765.SH')

# 标准化为统一格式
standardized_data = standardize_stock_basic(raw_data, 'tushare')

# 或直接创建 StockBasicData
stock_info = StockBasicData(
    code='600765',
    name='中航重机',
    industry='航空航天',
    pe=50.6094,
    pb=2.2754,
    total_mv=323.76,
)
```

### 技术分析数据获取

```python
from tradingagents.dataflows.schemas import StockHistoricalData, StockDailyData

# 创建日线数据
daily = StockDailyData(
    ts_code='600765.SH',
    trade_date='2026-01-24',
    open=45.32,
    high=46.10,
    low=44.98,
    close=45.67,
    volume=12345678,
    ma5=45.23,
    ma20=44.56,
    rsi6=58.5,
)

# 创建历史数据
historical_data = StockHistoricalData(
    code='600765',
    name='中航重机',
    market='CN',
    start_date='2025-12-01',
    end_date='2026-01-24',
    daily_data=[daily1, daily2, ...],
    latest_ma5=45.23,
    latest_rsi6=58.5,
    data_source='tushare',
)
```

## 数据单位规范

| 数据类型 | 单位 | 说明 |
|---------|------|------|
| 价格 | 元 (¥) | 股票价格 |
| 成交量 | 股 | 股票成交量（1手=100股） |
| 成交额 | 元 | 股票成交金额 |
| 市值 | 万元 | 总市值/流通市值 |
| 百分比 | % | 换手率、涨跌幅等 |
| 市盈率等 | 倍 | PE、PB、PS等估值指标 |

## 最佳实践

1. **基本面分析**：使用 `StockBasicData` + `standardize_stock_basic()`
2. **技术分析**：使用 `StockHistoricalData` + `StockDailyData`
3. **数据验证**：使用 `validate_stock_basic_data()` 验证数据完整性
4. **单位转换**：始终确保成交量转换为"股"单位
5. **缓存策略**：使用 MongoDB 缓存时，读取后调用 standardize_stock_basic() 标准化
"""
