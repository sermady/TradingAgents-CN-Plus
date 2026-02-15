# 统一Prompt构建优化指南

## 概述

为消除代码重复，我们创建了统一的`PromptBuilder`工具类（位于`tradingagents/agents/utils/prompt_builder.py`），用于构建辩论者和研究员的Prompt。

## 优化目标

将以下6个文件中的`_build_prompt`方法替换为使用`PromptBuilder`工具：

1. `tradingagents/agents/risk_mgmt/base_debator.py` - AggressiveDebator._build_prompt
2. `tradingagents/agents/risk_mgmt/base_debator.py` - ConservativeDebator._build_prompt
3. `tradingagents/agents/risk_mgmt/base_debator.py` - ModerateDebator._build_prompt（如果存在）
4. `tradingagents/agents/researchers/base_researcher.py` - BullResearcher._build_prompt
5. `tradingagents/agents/researchers/base_researcher.py` - BearResearcher._build_prompt
6. 其他Researcher类（如果存在）

## 优化步骤

### 步骤1：添加导入语句

在每个需要优化的文件顶部添加：

```python
from tradingagents.agents.utils.prompt_builder import build_debator_prompt
```

### 步骤2：替换方法实现

将原有的`_build_prompt`方法体替换为：

```python
def _build_prompt(self, ...):
    """构建辩论者prompt（使用统一工具）"""
    from tradingagents.agents.utils.prompt_builder import build_debator_prompt

    return build_debator_prompt(
        role="aggressive",  # 或根据self.debator_type调整
        description=self.description,
        goal=self.goal,
        focus=self.focus,
        reports=reports,
        history=history,
        current_responses=current_responses,
        trader_decision=trader_decision
    )
```

### 步骤3：删除辅助方法

如果文件中有`_format_other_responses`辅助方法，可以删除（已集成到PromptBuilder中）

### 步骤4：验证

运行Python语法检查：
```bash
python -m py_compile tradingagents/agents/risk_mgmt/base_debator.py
```

## 实际效果

- **减少代码**：约120行重复的prompt构建逻辑
- **统一接口**：所有Prompt构建通过`PromptBuilder`工具类
- **易于维护**：未来修改只需更新`PromptBuilder`类

## 注意事项

- 保持方法签名不变
- 保持返回值类型不变
- 确保导入语句位于文件顶部
- 修改后进行完整测试

## 迁移状态

- [ ] base_debator.py (AggressiveDebator)
- [ ] ConservativeDebator
- [ ] BullResearcher
- [ ] BearResearcher
- [ ] 其他Researcher类

---

**创建时间**: 2026-02-15
**优先级**: P1（高价值重复函数）
