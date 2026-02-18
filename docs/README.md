# 项目文档索引

## 快速导航

- **[开发指南](./CONTRIBUTING.md)** - 环境配置、开发流程、Git规范
- **[运维手册](./RUNBOOK.md)** - 部署、监控、故障处理
- **[架构说明](./ARCHITECTURE.md)** - 系统架构和技术栈
- **[快速入门](./GETTING_STARTED.md)** - 项目快速上手指南

## 报告分类

### 代码优化

- **[代码简化优化](./reports/code_simplification/)** - 代码简化和重构总结
  - [README](./reports/code_simplification/README.md) - 最终总结报告
  - [综合分析](./reports/code_simplification/comprehensive_analysis.md) - 重复模式全面分析

### 错误处理

- **[错误处理优化](./reports/error_handler/)** - 错误处理推广计划
  - [最终报告](./reports/error_handler/error_handler_promotion_final_report.md) - 推广实施总结
  - [优化指南](./reports/error_handler/error_handler_optimization_guide.md) - 使用指南

### 系统重构

- **[Alert Manager重构](./reports/alert_manager_refactoring_report.md)** - 告警管理器模块化拆分
- **[代码重构总结](./reports/code_refactoring_master_summary.md)** - 整体重构成果汇总
- **[Web应用迁移](./reports/web_app_migration_guide.md)** - Web应用重构指南

### 其他重要文档

- **[变更日志](./changes_summary_2026-01-30.md)** - 2026-01-30 变更总结
- **[中国分析师](./china_analyst_default_enable.md)** - 中国分析师功能说明
- **[数据质量增强](./data_quality_enhancement_summary.md)** - 数据质量提升总结

## 历史归档

- **[2026-01归档](./reports/historical/2026-01/)** - 2026年1月完成的项目报告

## 专题文档

- **[学术论文](./paper/)** - 研究论文和技术分析
- **[学习计划](./learning/)** - 技术学习记录
- **[项目计划](./plans/)** - 各类项目计划文档

## 文档组织原则

### 目录结构

```
docs/
├── README.md                    # 本文档：文档索引
├── CONTRIBUTING.md              # 开发指南
├── RUNBOOK.md                   # 运维手册
├── ARCHITECTURE.md              # 架构说明
├── GETTING_STARTED.md           # 快速入门
├── reports/                     # 各类报告
│   ├── code_simplification/     # 代码简化专题
│   ├── error_handler/           # 错误处理专题
│   ├── historical/              # 历史归档
│   └── *.md                     # 其他独立报告
├── paper/                       # 学术论文
├── learning/                    # 学习资料
└── plans/                       # 项目计划
```

### 命名规范

- **报告文档**: `<topic>_<type>_<date>.md` (如: `code_simplification_final_summary_20260215.md`)
- **技术文档**: `<topic>.md` (如: `ARCHITECTURE.md`)
- **指南文档**: `<topic>_guide.md` (如: `web_app_migration_guide.md`)

## 文档维护

### 添加新文档

1. **确定文档类型**: 报告、指南、架构、计划等
2. **选择正确位置**: 根据文档类型选择合适的目录
3. **使用规范命名**: 遵循项目命名规范
4. **更新索引**: 在本README.md中添加链接

### 归档旧文档

1. **判断归档时机**: 文档内容已过时或被替代
2. **创建归档目录**: `docs/reports/historical/YYYY-MM/`
3. **移动文档**: 将旧文档移动到归档目录
4. **更新引用**: 更新其他文档中的引用链接

## 文档统计

| 类别 | 文档数量 | 最后更新 |
|------|----------|----------|
| 核心文档 | 4 | 2026-02 |
| 代码优化 | 2 | 2026-02 |
| 错误处理 | 2 | 2026-02 |
| 系统重构 | 3 | 2026-02 |
| 其他报告 | 3 | 2026-01 |
| 学术论文 | 1+ | - |

## 贡献指南

文档贡献遵循以下原则：

1. **准确性**: 确保技术信息准确无误
2. **清晰性**: 使用简洁明了的语言
3. **完整性**: 包含必要的背景和上下文
4. **时效性**: 及时更新过时内容
5. **格式规范**: 遵循Markdown格式规范

---

**文档维护**: 项目团队
**最后更新**: 2026-02-19
**版本**: 1.0
