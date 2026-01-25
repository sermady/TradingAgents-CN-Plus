# 修复新闻数据获取使用前端指定分析日期

**问题**: 新闻工具使用 `datetime.now()` 获取系统时间，而不是前端传入的分析日期

**影响**:
- 用户输入2024-06-21分析，但获取的是2026-01-25的新闻数据
- 导致数据时间与分析日期不一致

## 修复方案

### 文件1: tradingagents/tools/unified_news_tool.py

**修改**:
```python
# 修改前 (第283-288行)
def _get_a_share_news(self, stock_code: str, max_news: int, model_info: str = "") -> str:
    """获取A股新闻"""
    logger.info(f"[统一新闻工具] 获取A股 {stock_code} 新闻")

    # 获取当前日期
    curr_date = datetime.now().strftime("%Y-%m-%d")  # ❌ 错误！使用系统时间

# 修改后
def _get_a_share_news(self, stock_code: str, max_news: int, model_info: str = "",
                      analysis_date: str = None) -> str:
    """获取A股新闻

    Args:
        stock_code: 股票代码
        max_news: 最大新闻数量
        model_info: 模型信息
        analysis_date: 分析日期 (YYYY-MM-DD 格式)  # ✅ 新增参数
    """
    logger.info(f"[统一新闻工具] 获取A股 {stock_code} 新闻，分析日期: {analysis_date}")

    # 使用前端传入的分析日期，如果没有则使用当前日期
    if analysis_date:
        curr_date = analysis_date
        logger.info(f"[统一新闻工具] ✅ 使用前端指定的分析日期: {curr_date}")
    else:
        curr_date = datetime.now().strftime("%Y-%m-%d")
        logger.warning(f"[统一新闻工具] ⚠️ 未提供分析日期，使用系统时间: {curr_date}")
```

### 文件2: tradingagents/tools/unified_news_tool.py

**修改 `get_stock_news_unified` 方法签名**:
```python
# 修改前
def get_stock_news_unified(self, stock_code: str, max_news: int = 10,
                          model_info: str = "") -> str:

# 修改后
def get_stock_news_unified(self, stock_code: str, max_news: int = 10,
                          model_info: str = "", analysis_date: str = None) -> str:
    """
    统一新闻获取接口

    Args:
        stock_code: 股票代码
        max_news: 最大新闻数量
        model_info: 模型信息
        analysis_date: 分析日期 (YYYY-MM-DD 格式)  # ✅ 新增
    """
    # 传递 analysis_date 给各子方法
    if stock_type == "A股":
        result = self._get_a_share_news(stock_code, max_news, model_info, analysis_date)
    elif stock_type == "港股":
        result = self._get_hk_share_news(stock_code, max_news, model_info, analysis_date)
    # ...
```

### 文件3: tradingagents/agents/utils/agent_utils.py

**修改 `create_unified_news_tool` 函数**:
```python
# 修改前
def create_unified_news_tool(toolkit):
    def get_stock_news_unified(stock_code: str, max_news: int = 10) -> str:
        analyzer = UnifiedNewsAnalyzer(toolkit)
        return analyzer.get_stock_news_unified(stock_code, max_news)
    get_stock_news_unified.name = "get_stock_news_unified"
    return get_stock_news_unified

# 修改后
def create_unified_news_tool(toolkit, analysis_date: str = None):
    """
    创建统一新闻工具

    Args:
        toolkit: 工具包
        analysis_date: 分析日期 (YYYY-MM-DD 格式)  # ✅ 新增
    """
    def get_stock_news_unified(stock_code: str, max_news: int = 10) -> str:
        analyzer = UnifiedNewsAnalyzer(toolkit)
        return analyzer.get_stock_news_unified(stock_code, max_news,
                                                 model_info="",
                                                 analysis_date=analysis_date)
    get_stock_news_unified.name = "get_stock_news_unified"
    return get_stock_news_unified
```

### 文件4: tradingagents/graph/setup.py

**修改工具创建时的日期传递**:
```python
# 修改前
unified_news_tool = create_unified_news_tool(toolkit)

# 修改后
# 从配置中获取分析日期
analysis_date = config.get("analysis_date", datetime.now().strftime("%Y-%m-%d"))
logger.info(f"📅 [工具创建] 使用分析日期: {analysis_date}")

unified_news_tool = create_unified_news_tool(toolkit, analysis_date=analysis_date)
```

### 文件5: tradingagents/tools/unified_news_tool.py

**修改 `_get_news_from_database` 方法**:
```python
# 修改前 (第94-125行)
def _get_news_from_database(self, stock_code: str, max_news: int = 10) -> str:
    # ...
    thirty_days_ago = datetime.now() - timedelta(days=30)  # ❌ 使用系统时间
    query_list = [
        {'symbol': clean_code, 'publish_time': {'$gte': thirty_days_ago}},
        # ...
    ]

# 修改后
def _get_news_from_database(self, stock_code: str, max_news: int = 10,
                            analysis_date: str = None) -> str:
    """从数据库获取新闻

    Args:
        stock_code: 股票代码
        max_news: 最大新闻数量
        analysis_date: 分析日期  # ✅ 新增
    """
    # 使用分析日期作为基准
    if analysis_date:
        try:
            base_date = datetime.strptime(analysis_date, "%Y-%m-%d")
        except:
            base_date = datetime.now()
    else:
        base_date = datetime.now()

    # 查询分析日期之前30天的新闻
    thirty_days_ago = base_date - timedelta(days=30)

    # 同时查询分析日期之后1天的新闻（包含当天）
    one_day_after = base_date + timedelta(days=1)

    query_list = [
        # 优先查询分析日期前后的新闻
        {
            'symbol': clean_code,
            'publish_time': {
                '$gte': thirty_days_ago,
                '$lte': one_day_after
            }
        },
        # ...
    ]
```

## 修复验证

### 测试用例
```python
def test_news_uses_analysis_date():
    """测试新闻工具使用分析日期"""
    from tradingagents.tools.unified_news_tool import UnifiedNewsAnalyzer
    from tradingagents.utils.toolkit import Toolkit

    # 模拟用户指定2024-06-21
    analysis_date = "2024-06-21"
    toolkit = Toolkit()

    analyzer = UnifiedNewsAnalyzer(toolkit)
    result = analyzer._get_a_share_news("605589", 10, "", analysis_date)

    # 验证：返回的新闻应该不包含2026年的数据
    assert "2026" not in result
    assert "2024" in result
```

## 影响范围

### 修改的文件
1. `tradingagents/tools/unified_news_tool.py` - 核心修改
2. `tradingagents/agents/utils/agent_utils.py` - 工具创建
3. `tradingagents/graph/setup.py` - 工具初始化

### 数据获取时间范围
**修复前**:
- 使用 `datetime.now()` → 2026-01-25
- 查询 2025-01-25 到 2026-01-25 的新闻

**修复后**:
- 使用 `analysis_date` → 2024-06-21 (用户指定)
- 查询 2024-05-22 到 2024-06-22 的新闻

## 其他需要检查的数据获取点

1. **东方财富新闻** - `get_realtime_stock_news.invoke()`
2. **Google News** - `get_google_news()`
3. **Reddit News** - `get_reddit_news()`
4. **基本面数据** - `get_stock_fundamentals_unified()`
5. **技术指标数据** - `get_stock_market_data_unified()`

所有这些都需要确保使用前端传入的分析日期。
