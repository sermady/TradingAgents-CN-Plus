# 统一Prompt构建优化指南

## 概述

为消除代码重复，我们创建了统一的`PromptBuilder`工具类（位于`tradingagents/agents/utils/prompt_builder.py`），用于构建辩论者和研究员的Prompt。

## 优化目标

将以下6个文件中的`_build_prompt`方法替换为使用`PromptBuilder`工具：

### 辩论者类（已优化✅）
1. ✅ `tradingagents/agents/risk_mgmt/base_debator.py` - AggressiveDebator._build_prompt
2. ✅ `tradingagents/agents/risk_mgmt/base_debator.py` - ConservativeDebator._build_prompt
3. ✅ `tradingagents/agents/risk_mgmt/base_debator.py` - NeutralDebator._build_prompt

### 研究员类（保留原有实现⚠️）
4. ⚠️ `tradingagents/agents/researchers/base_researcher.py` - BullResearcher._build_prompt
   - **原因**: Prompt内容差异大，包含大量特定细节（数据验证清单、强制要求等）
   - **状态**: 已添加PromptBuilder导入，但保留原有实现
5. ⚠️ `tradingagents/agents/researchers/base_researcher.py` - BearResearcher._build_prompt
   - **原因**: 同上
   - **状态**: 已添加PromptBuilder导入，但保留原有实现

## 已完成的优化

### 辩论者类优化

已修改的文件:
- `tradingagents/agents/risk_mgmt/base_debator.py`
  - ✅ AggressiveDebator: 使用`build_debator_prompt`工具函数
  - ✅ ConservativeDebator: 使用`build_debator_prompt`工具函数
  - ✅ NeutralDebator: 使用`build_debator_prompt`工具函数
  - ✅ 删除重复的`_format_other_responses`方法
  - ✅ 添加`from tradingagents.agents.utils.prompt_builder import build_debator_prompt`导入

### 研究员类导入

已添加导入但未修改实现:
- `tradingagents/agents/researchers/base_researcher.py`
  - ✅ 添加`from tradingagents.agents.utils.prompt_builder import build_researcher_prompt`导入
  - ⚠️ BullResearcher和BearResearcher保留原有实现（内容差异大）

## 实际效果

- **减少代码**：约100行重复的prompt构建逻辑（3个辩论者类）
- **统一接口**：所有辩论者通过`PromptBuilder`工具类
- **保持质量**：研究员类保留特定内容，确保分析质量
- **易于维护**：未来新增简单辩论者可直接使用工具类

## 注意事项

- 研究员类的prompt包含大量特定内容（数据验证、强制要求等），不适合完全统一
- 辩论者类的prompt结构相似，适合统一
- 保持方法签名不变
- 保持返回值类型不变

## 迁移状态

- [x] AggressiveDebator
- [x] ConservativeDebator
- [x] NeutralDebator
- [ ] BullResearcher（保留原有实现）
- [ ] BearResearcher（保留原有实现）

---

**创建时间**: 2026-02-15
**更新时间**: 2026-02-15
**优先级**: P1（高价值重复函数）
