# 600765财务数据缺失 - 完整诊断报告与解决方案

## 问题描述
在分析股票 600765 时出现"核心财务数据缺失"问题

## 根本原因
AKShare财务数据接口不兼容：
- `stock_financial_analysis_indicator(600765)` 返回空数据
- `stock_financial_abstract(600765)` 返回价格历史数据，不包含财务指标（PE、PB、ROE等）

## 数据状态

### MongoDB数据
```
记录存在: 1条
报告期: 20260331
数据源: akshare
问题: 财务指标字段全部为 None
```

### 关键字段检查
```
✅ 基础字段: code, symbol, report_period, data_source
❌ 财务字段: pe, pb, roe, net_profit, total_revenue, total_assets
```

## 解决方案

### 方案1: 启用 Tushare 数据源（推荐）

**步骤：**
1. 在 Web后台配置中启用 Tushare 数据源
2. 配置有效的 Tushare API Token
3. 设置 Tushare 为最高优先级
4. 重新同步 600765 财务数据

**操作：**
```bash
# 1. 配置 Tushare Token（获取方式：https://tushare.pro/）
# 编辑 .env 文件添加：
TUSHARE_TOKEN=your_actual_token_here

# 2. 重新同步财务数据
python scripts/sync_financial_data.py 600765
```

### 方案2: 修复 AKShare 接口兼容性（需要开发）

**修改文件：** `scripts/sync_financial_data.py`

**修改位置：** 第56-86行

**修改内容：**
```python
# 原代码：使用 stock_financial_analysis_indicator（对某些股票返回空）
def fetch_financial_indicator():
    return ak.stock_financial_analysis_indicator(symbol=code6)

# 新代码：尝试多个接口
def fetch_financial_indicator():
    # 方案A: stock_financial_analysis_indicator
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code6)
        if df is not None and not df.empty:
            return df
    except:
        pass
    
    # 方案B: stock_a_indicator
    try:
        df = ak.stock_a_indicator(symbol=code6)
        if df is not None and not df.empty:
            return df
    except:
        pass
    
    # 方案C: stock_a_lg_indicator（历史数据）
    try:
        df = ak.stock_a_lg_indicator(symbol=code6)
        if df is not None and not df.empty:
            return df
    except:
        pass
    
    return None
```

### 方案3: 手动补充数据（临时方案）

如果急需查看分析结果，可以手动在 MongoDB 中补充600765 的财务数据：

**MongoDB 操作：**
```javascript
// 连接 tradingagents 数据库
use tradingagents

// 更新 stock_financial_data 集合
db.stock_financial_data.updateOne(
  { "code": "600765", "report_period": "20260331" },
  {
    $set: {
      "pe": 15.5,
      "pb": 1.2,
      "roe": 12.3,
      "net_profit": 123456.78,
      "revenue": 567890.12,
      "total_assets": 789012.34,
      "total_hldr_eqy_exc_min_int": 567890.34,
      "updated_at": new Date()
    }
  }
)
)
```

## 推荐方案

### 短期解决方案（立即可用）：
✅ **启用 Tushare 数据源并重新同步**

### 长期解决方案（一劳永逸）：
✅ **修复 AKShare 接口兼容性**，支持多个数据源降级

## 数据源对比

| 数据源 | 优点 | 缺点 |
|--------|------|------|
| **Tushare** | 数据最准确，API稳定 | 需要API Token，有配额限制 |
| **AKShare** | 免费，数据全面 | 部分股票数据不完整 |
| **BaoStock** | 免费，API稳定 | 数据更新较慢 |

## 验证步骤

### 1. 重新同步后验证
```bash
# 检查数据
python scripts/check_financial_data.py

# 查询 MongoDB
# 运行：scripts/diagnose_600765_financial_data_quick.py
```

### 2. 测试分析流程
```bash
# 重新运行 600765 分析
# 在 Web 界面或命令行中重新发起分析
```

## 附件

测试脚本：
- `scripts/diagnose_600765_financial_data_quick.py` - 快速诊断脚本
- `scripts/test_financial_abstract.py` - 数据结构测试脚本
- `scripts/test_akshare_600765.py` - AKShare接口测试脚本
- `scripts/test_akshare_detailed.py` - AKShare详细测试

## 预期结果

修复后，600765 的基本面分析应包含：
```
✅ PE (市盈率)
✅ PB (市净率)
✅ ROE (净资产收益率)
✅ 净利润
✅ 营业收入
✅ 总资产
✅ 资产负债率
```

---

**生成时间**: 2025-01-18
**诊断版本**: v1.0
