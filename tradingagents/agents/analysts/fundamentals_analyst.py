# -*- coding: utf-8 -*-
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name
from langchain_core.messages import AIMessage

logger = get_logger("analysts.fundamentals")


def create_fundamentals_analyst(llm, toolkit=None):
    """
    创建基本面分析师节点

    Args:
        llm: 语言模型实例
        toolkit: 工具包（可选，用于兼容性）

    Returns:
        fundamentals_analyst_node: 基本面分析师节点函数
    """

    @log_analyst_module("fundamentals")
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data and metadata
        financial_data = state.get("financial_data", "")
        data_quality_score = state.get("data_quality_score", 0.0)
        data_sources = state.get("data_sources", {})
        data_issues = state.get("data_issues", {})

        # 检查数据质量
        financial_source = data_sources.get("financial", "unknown")
        financial_issues = data_issues.get("financial", [])

        if not financial_data or "❌" in financial_data:
            logger.warning(
                f"[Fundamentals Analyst] Financial data unavailable for {ticker} (source: {financial_source})"
            )
            financial_data = (
                "警告：财务数据不可用。已尝试从多个数据源获取但均失败。\n"
                "请检查网络连接或稍后重试。"
            )

        logger.info(
            f"[Fundamentals Analyst] Analyzing {ticker} on {current_date} (quality: {data_quality_score:.2f}, source: {financial_source})"
        )

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        # 记录数据质量问题到日志（不在提示词中显示）
        if financial_issues:
            for issue in financial_issues[:3]:
                logger.warning(
                    f"[Fundamentals Analyst] Data issue for {ticker}: {issue.get('message', '')}"
                )

        # 获取 metadata 信息（如有）
        data_metadata = state.get("data_metadata", {})

        # 构建 metadata 提示
        # 注意：PS修正信息已由 Data Coordinator 添加到 financial_data 中，这里不再重复添加
        metadata_info = "\n- **成交量单位**: 手 (1手=100股)"

        system_message = f"""你是一位专业的股票基本面分析师。
请基于以下**真实财务数据**对 {company_name} ({ticker}) 进行深度的基本面分析。

=== 数据信息 ===
- 数据来源: {financial_source}
- 数据日期: {current_date}（历史数据）
{metadata_info}

=== 财务数据 ===
{financial_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的财务数据进行分析，绝对禁止编造数据。
2. **财务状况**：分析营收、利润、现金流等核心指标。
3. **估值分析**：分析PE、PB、PS、PEG等估值指标，判断当前股价是否低估/高估。
   - ⚠️ **特别注意PS比率**：如果财务数据中有PS修正标记（"⚠️ **PS比率修正**"），请使用修正后的PS值进行分析。
    - **估值指标计算公式（必须严格遵守）：**
      
      **【重要】PE指标区分说明（必看）：**
      
      📊 **PE_TTM（滚动市盈率）** - 市场常用估值指标
      - **公式**：PE_TTM = 总市值 / TTM净利润
      - **TTM净利润**：过去12个月滚动归母净利润（Trailing Twelve Months）
      - **特点**：反映公司最近12个月的盈利能力，更及时
      - **用途**：同花顺、东方财富等APP显示的PE通常是PE_TTM
      - ⚠️ **验证时必须使用TTM净利润，不能用年报归母净利润**
      
      📊 **PE静态（静态市盈率）** - 年报基础估值指标  
      - **公式**：PE静态 = 总市值 / 年报归母净利润
      - **归母净利润**：最新年度报告的归属母公司净利润
      - **特点**：基于完整财年的审计数据，更稳定
      - **用途**：适合年度对比和长期分析
      - ⚠️ **使用年报数据计算，可能与PE_TTM差异很大**
      
      🔴 **关键区别示例**：
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
      
      **报告撰写要求**：
      - 必须明确区分报告中使用的是PE_TTM还是PE静态
      - 如果同时引用两种PE，请分别说明计算依据
      - 不要混淆两种PE指标进行横向比较
      
      **其他估值指标**：
      - **PB（市净率）**：PB = 总市值 / 归母净资产
      - **PS（市销率）**：PS = 总市值 / 总营收
      
      📊 **PS_TTM（滚动市销率）vs PS（静态市销率）** - 【新增重要说明】
      
      **定义与区别**：
      - **PS_TTM（滚动市销率）**：使用最近12个月（TTM）的营业收入计算
        - 公式：PS_TTM = 总市值 / TTM营业收入
        - 特点：反映公司最近12个月的营收水平，更及时、更平滑季节性波动
        - 用途：同花顺、东方财富等APP显示的PS通常是PS_TTM
      
      - **PS（静态市销率）**：使用单季度或年度营业收入计算
        - 公式：PS = 总市值 / 营业收入（单期）
        - 特点：基于特定时期的营收数据，可能受季节性影响
        - 用途：适合季度对比和特定时期分析
      
      🔴 **关键区别示例**（与PE_TTM/PE静态类似）：
      ```
      假设：
      - 总市值 = 268.81亿元
      - PS_TTM = 2.5倍（基于TTM营收107.5亿元）
      - PS（静态）= 3.33倍（基于年度营收80.72亿元）
      
      计算验证：
      ✓ PS_TTM = 268.81 ÷ 107.5 = 2.5倍（反映最近12个月营收能力）
      ✗ PS静态 = 268.81 ÷ 80.72 = 3.33倍（仅反映单期营收）
      
      差异原因：TTM营收（107.5亿）vs 年度营收（80.72亿）= 营收口径不同！
      ```
      
      **报告撰写要求（PS指标）**：
      - **必须明确区分**：报告中使用的是PS_TTM还是PS静态，不得混淆
      - **优先使用PS_TTM**：如数据可用，优先使用PS_TTM进行估值分析
      - **数据来源说明**：明确标注PS数据的来源和计算依据
      - **双指标对比**：如同时提供PS_TTM和PS静态，需说明两者的差异及原因
      
      **验算要求**：
      - PS_TTM 必须用 **TTM营业收入** 验算
      - PS静态 用 **单期营业收入** 验算
      - 如果PS_TTM缺失，可用PS静态代替，但必须明确说明
 4. **盈利能力**：分析毛利率、净利率、ROE等指标。
5. **数据异常处理**：
    - ⚠️ **【核心】PE验算注意事项（必读）**：
      
      **🔴 最重要的区别：PE_TTM vs PE静态**
      
      当报告中出现以下情况时，**这不是错误，而是正常现象**：
      - PE_TTM（25.7倍） × 年报净利润（7.60亿） ≠ 总市值（268.81亿）
      - 计算结果：195.32亿 vs 实际市值268.81亿（差异70亿+）
      
      **✅ 正确理解：**
      - PE_TTM使用的是**TTM净利润**（约10.46亿），不是年报净利润
      - 反推验证：268.81亿 ÷ 25.7 = 10.46亿（TTM净利润）
      - 所以：25.7 × 10.46 ≈ 268.81亿 ✓
      
      **❌ 常见错误：**
      - 用年报净利润（7.60亿）去验算PE_TTM（25.7倍）
      - 误以为"PE_TTM × 净利润 = 市值"就一定成立
      - 混淆PE_TTM和PE静态的概念
      
      **报告撰写要求**：
      - 如果验算时发现差异，请先检查使用的是哪种净利润口径
      - Tushare的PE_TTM是官方计算值，通常准确，不需要"修正"
      - 如需验算，请明确说明："使用TTM净利润XX亿元，计算得PE_TTM = XX倍"
      
    - **其他指标验算**：
      - PE_TTM 必须用 **TTM净利润** 验算，绝对不能用单期归母净利润
      - PE静态 用 **年报归母净利润** 验算
      - PB 用 **净资产** 验算
      - PS 用 **营收** 验算
    - 如果发现PB、PS等估值指标异常，请使用**正确口径**的市值和营收/净利润重新计算验证
   - **验算格式要求**：使用清晰的文本格式展示验算过程，不要使用复杂的LaTeX公式
     - ✅ **推荐格式**：
       ```
       PS计算：
         • 总市值：XX亿元
         • 营业收入：XX亿元
         • 计算：XX ÷ XX = XX倍
         • 报告PS值：XX倍
         • 结果：✓ 一致
       ```
   - 如果数据有明显错误，请在报告中指出并说明正确的计算方法
6. **投资建议规范**：
   - 建议等级：使用"强烈买入/买入/谨慎买入/持有/谨慎卖出/卖出/强烈卖出/中性观望"之一
   - 避免使用绝对化表述（如"必须"、"务必"、"绝对"、"坚决"）
   - 提供合理的目标价位区间，并说明估值依据
   - 给出明确的投资理由和风险评估

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）基本面分析报告**
## 一、公司概况与财务摘要
## 二、盈利能力与成长性分析
## 三、估值水平评估
**⚠️ 本章必须明确区分估值指标（PE、PS都有TTM和静态两种口径）：**

### PE指标区分：
- **PE_TTM（滚动市盈率）**：使用TTM净利润计算，反映最近12个月盈利能力
- **PE静态**：使用年报归母净利润计算，反映完整财年表现
- **必须说明**：报告使用的是哪种PE，以及数据来源

### PS指标区分：
- **PS_TTM（滚动市销率）**：使用TTM营业收入计算，反映最近12个月营收水平
- **PS（静态市销率）**：使用单期营业收入计算，可能受季节性影响
- **优先使用PS_TTM**：如数据可用，应优先使用PS_TTM进行估值分析

**建议格式示例**：
```
### 估值指标分析
**当前估值水平**：

#### 市盈率（PE）指标：
- PE_TTM：25.7倍（基于TTM净利润10.46亿元，市值268.81亿元）
- PE静态：35.4倍（基于年报归母净利润7.60亿元，市值268.81亿元）
- 数据来源：Tushare官方计算

#### 市销率（PS）指标：
- PS_TTM：2.5倍（基于TTM营收107.5亿元，市值268.81亿元）【优先使用】
- PS（静态）：3.33倍（基于年度营收80.72亿元，市值268.81亿元）
- 说明：PS_TTM更能反映公司最近12个月的营收能力，已进行验算确认

**估值判断**：
- PE_TTM 25.7倍处于行业中等水平...
- PS_TTM 2.5倍相比PS静态3.33倍更能反映真实营收水平...
- 注意：PE_TTM与PE静态差异较大（37.7%），原因是TTM净利润（10.46亿）高于年报净利润（7.60亿）...
```

## 四、投资建议与目标价

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失或异常，请明确说明。
⚠️ **特别提醒**：
- 报告中引用的**PE指标**必须明确是PE_TTM还是PE静态，避免混淆
- 报告中引用的**PS指标**必须明确是PS_TTM还是PS静态，优先使用PS_TTM，如使用PS静态必须说明原因
"""

        messages = [
            ("system", system_message),
            ("human", f"请生成 {company_name} ({ticker}) 的基本面分析报告。"),
        ]

        try:
            response = llm.invoke(messages)
            return {"fundamentals_report": response.content, "messages": [response]}
        except Exception as e:
            logger.error(f"[Fundamentals Analyst] LLM调用失败: {e}", exc_info=True)
            return {
                "fundamentals_report": f"❌ 基本面分析失败: {str(e)}",
                "messages": [],
            }

    return fundamentals_analyst_node
