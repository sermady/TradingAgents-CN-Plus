# -*- coding: utf-8 -*-
"""
代码简化分析报告生成器
检测重复代码、超大文件和简化机会
"""

import os
import re
import ast
import hashlib
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
import json


@dataclass
class FunctionInfo:
    """函数信息"""
    name: str
    filepath: str
    line_start: int
    line_end: int
    line_count: int
    content_hash: str
    content: str
    is_method: bool = False
    class_name: Optional[str] = None


@dataclass
class DuplicateGroup:
    """重复代码组"""
    pattern: str
    occurrences: List[Tuple[str, int, int]]  # (filepath, line_start, line_end)
    similarity: float


@dataclass
class FileAnalysis:
    """文件分析结果"""
    filepath: str
    total_lines: int
    function_count: int
    class_count: int
    functions: List[FunctionInfo] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


class CodeSimplificationAnalyzer:
    """代码简化分析器"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.files: List[FileAnalysis] = []
        self.duplicate_functions: List[DuplicateGroup] = []
        self.duplicate_patterns: List[DuplicateGroup] = []
        self.large_files: List[FileAnalysis] = []

        # 要扫描的目录
        self.target_dirs = [
            "app/services",
            "app/worker",
            "app/routers",
            "tradingagents",
        ]

        # 跳过的目录
        self.skip_dirs = {
            'node_modules', 'venv', '__pycache__', '.git',
            '.pytest_cache', '.mypy_cache', 'dist', 'build',
            'frontend', 'logs', 'temp', 'exports'
        }

    def analyze(self):
        """执行完整分析"""
        print("开始代码简化分析...")

        # 1. 收集所有Python文件
        python_files = self._collect_python_files()
        print(f"找到 {len(python_files)} 个Python文件")

        # 2. 分析每个文件
        for filepath in python_files:
            analysis = self._analyze_file(filepath)
            if analysis:
                self.files.append(analysis)

        # 3. 识别超大文件
        self._identify_large_files()

        # 4. 检测重复函数
        self._detect_duplicate_functions()

        # 5. 检测重复模式
        self._detect_duplicate_patterns()

        # 6. 生成报告
        self._generate_report()

    def _collect_python_files(self) -> List[Path]:
        """收集Python文件"""
        files = []

        for target_dir in self.target_dirs:
            target_path = self.project_path / target_dir
            if not target_path.exists():
                continue

            for py_file in target_path.rglob("*.py"):
                # 检查是否在跳过目录中
                if any(skip in str(py_file) for skip in self.skip_dirs):
                    continue
                files.append(py_file)

        return sorted(files)

    def _analyze_file(self, filepath: Path) -> Optional[FileAnalysis]:
        """分析单个文件"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            total_lines = len(lines)

            # 解析AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                return FileAnalysis(
                    filepath=str(filepath.relative_to(self.project_path)),
                    total_lines=total_lines,
                    function_count=0,
                    class_count=0,
                    issues=["语法错误，无法解析"]
                )

            functions = []
            class_count = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_count += 1
                    # 分析类中的方法
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            func_info = self._extract_function_info(
                                item, filepath, content, lines, True, node.name
                            )
                            if func_info:
                                functions.append(func_info)

                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # 只处理模块级别的函数
                    if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                        func_info = self._extract_function_info(
                            node, filepath, content, lines, False
                        )
                        if func_info:
                            functions.append(func_info)

            # 识别问题
            issues = []
            if total_lines > 1000:
                issues.append(f"超大文件 ({total_lines} 行)")
            if total_lines > 500 and class_count == 0 and len(functions) > 10:
                issues.append("函数过多，建议按功能分组")

            return FileAnalysis(
                filepath=str(filepath.relative_to(self.project_path)),
                total_lines=total_lines,
                function_count=len(functions),
                class_count=class_count,
                functions=functions,
                issues=issues
            )

        except Exception as e:
            return None

    def _extract_function_info(
        self,
        node: ast.FunctionDef,
        filepath: Path,
        content: str,
        lines: List[str],
        is_method: bool,
        class_name: Optional[str] = None
    ) -> Optional[FunctionInfo]:
        """提取函数信息"""
        try:
            line_start = node.lineno
            line_end = node.end_lineno or line_start
            func_lines = lines[line_start - 1:line_end]
            func_content = '\n'.join(func_lines)

            # 标准化内容（移除变量名，保留结构）
            normalized = self._normalize_function(func_content)
            content_hash = hashlib.md5(normalized.encode()).hexdigest()

            return FunctionInfo(
                name=node.name,
                filepath=str(filepath.relative_to(self.project_path)),
                line_start=line_start,
                line_end=line_end,
                line_count=line_end - line_start + 1,
                content_hash=content_hash,
                content=func_content,
                is_method=is_method,
                class_name=class_name
            )
        except Exception:
            return None

    def _normalize_function(self, content: str) -> str:
        """标准化函数内容用于比较"""
        # 移除注释
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        # 移除字符串内容
        content = re.sub(r'["\'][^"\']*["\']', '"""', content)
        # 标准化空白
        content = re.sub(r'\s+', ' ', content)
        # 移除具体变量名（保留结构）
        content = re.sub(r'\b[a-z_][a-z0-9_]*\b', 'VAR', content)
        return content.strip()

    def _identify_large_files(self):
        """识别超大文件"""
        self.large_files = [
            f for f in self.files
            if f.total_lines > 1000
        ]
        self.large_files.sort(key=lambda x: x.total_lines, reverse=True)

    def _detect_duplicate_functions(self):
        """检测重复函数"""
        # 按hash分组
        hash_groups: Dict[str, List[FunctionInfo]] = defaultdict(list)

        for file_analysis in self.files:
            for func in file_analysis.functions:
                # 只分析超过10行的函数
                if func.line_count >= 10:
                    hash_groups[func.content_hash].append(func)

        # 找出重复的
        for hash_val, funcs in hash_groups.items():
            if len(funcs) > 1:
                occurrences = [
                    (f.filepath, f.line_start, f.line_end)
                    for f in funcs
                ]
                self.duplicate_functions.append(DuplicateGroup(
                    pattern=funcs[0].name,
                    occurrences=occurrences,
                    similarity=1.0
                ))

    def _detect_duplicate_patterns(self):
        """检测重复代码模式"""
        # 常见的重复模式
        patterns = [
            # 错误处理模式
            (r'try:\s*.*?except\s+Exception\s+as\s+\w+:\s*logger\.error',
             "重复的错误处理模式"),
            # CRUD模式
            (r'def\s+(create|get|update|delete)_\w+\s*\([^)]*\)\s*->\s*\w+',
             "CRUD操作模式"),
            # API调用模式
            (r'requests\.(get|post)\s*\([^)]*\)\s*\.json\(\)',
             "API调用模式"),
            # 缓存检查模式
            (r'if\s+\w+\s+in\s+\w+:\s*return\s+\w+\[\w+\]',
             "缓存检查模式"),
        ]

        for file_analysis in self.files:
            try:
                filepath = self.project_path / file_analysis.filepath
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for pattern, desc in patterns:
                    matches = list(re.finditer(pattern, content, re.DOTALL))
                    if len(matches) > 2:  # 出现3次以上
                        occurrences = [
                            (file_analysis.filepath, m.start(), m.end())
                            for m in matches
                        ]
                        self.duplicate_patterns.append(DuplicateGroup(
                            pattern=desc,
                            occurrences=occurrences,
                            similarity=0.8
                        ))
            except Exception:
                pass

    def _generate_report(self):
        """生成分析报告"""
        report_path = self.project_path / "docs" / "reports" / "code_simplification_analysis.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# TradingAgents-CN 代码简化分析报告\n\n")
            f.write(f"**分析时间**: {self._get_timestamp()}\n")
            f.write(f"**分析文件数**: {len(self.files)}\n")
            f.write(f"**项目路径**: {self.project_path}\n\n")

            # 1. 执行摘要
            f.write("## 执行摘要\n\n")
            f.write(f"- **超大文件 (>1000行)**: {len(self.large_files)} 个\n")
            f.write(f"- **重复函数**: {len(self.duplicate_functions)} 组\n")
            f.write(f"- **重复模式**: {len(self.duplicate_patterns)} 类\n\n")

            # 2. 超大文件详情
            f.write("## 1. 超大文件分析 (P0 - 高优先级)\n\n")
            if self.large_files:
                f.write("| 文件路径 | 行数 | 函数数 | 类数 | 建议操作 |\n")
                f.write("|---------|------|--------|------|----------|\n")
                for file in self.large_files[:20]:  # Top 20
                    suggestion = self._get_split_suggestion(file)
                    f.write(f"| {file.filepath} | {file.total_lines} | "
                           f"{file.function_count} | {file.class_count} | {suggestion} |\n")

                f.write("\n### 拆分建议详情\n\n")
                for file in self.large_files[:10]:
                    f.write(f"#### {file.filepath}\n")
                    f.write(f"- **当前行数**: {file.total_lines}\n")
                    f.write(f"- **建议**: {self._get_detailed_suggestion(file)}\n\n")
            else:
                f.write("未发现超大文件。\n")

            # 3. 重复函数
            f.write("\n## 2. 重复函数检测 (P1 - 中优先级)\n\n")
            if self.duplicate_functions:
                f.write(f"发现 {len(self.duplicate_functions)} 组重复函数:\n\n")
                for i, dup in enumerate(self.duplicate_functions[:15], 1):
                    f.write(f"### 2.{i} {dup.pattern}\n")
                    f.write(f"- **相似度**: {dup.similarity * 100:.0f}%\n")
                    f.write(f"- **出现次数**: {len(dup.occurrences)}\n")
                    f.write("- **位置**:\n")
                    for filepath, start, end in dup.occurrences:
                        f.write(f"  - `{filepath}:{start}-{end}`\n")
                    f.write(f"- **建议**: 提取到公共模块 `utils/common.py`\n\n")
            else:
                f.write("未发现明显重复的函数。\n")

            # 4. 重复模式
            f.write("\n## 3. 重复代码模式 (P1 - 中优先级)\n\n")
            if self.duplicate_patterns:
                pattern_summary: Dict[str, int] = defaultdict(int)
                for p in self.duplicate_patterns:
                    pattern_summary[p.pattern] += len(p.occurrences)

                f.write("| 模式类型 | 出现次数 | 建议 |\n")
                f.write("|---------|---------|------|\n")
                for pattern, count in sorted(pattern_summary.items(), key=lambda x: -x[1]):
                    suggestion = self._get_pattern_suggestion(pattern)
                    f.write(f"| {pattern} | {count} | {suggestion} |\n")
            else:
                f.write("未发现重复代码模式。\n")

            # 5. 文件统计
            f.write("\n## 4. 文件复杂度统计\n\n")
            f.write("### 4.1 最复杂的文件 (按函数数量)\n\n")
            complex_files = sorted(
                self.files,
                key=lambda x: x.function_count,
                reverse=True
            )[:15]

            f.write("| 文件路径 | 总行数 | 函数数 | 类数 |\n")
            f.write("|---------|--------|--------|------|\n")
            for file in complex_files:
                f.write(f"| {file.filepath} | {file.total_lines} | "
                       f"{file.function_count} | {file.class_count} |\n")

            # 6. 优先级行动计划
            f.write("\n## 5. 优先级行动计划\n\n")
            f.write("### P0 - 立即处理 (本周)\n")
            f.write(self._generate_p0_actions())

            f.write("\n### P1 - 短期处理 (本月)\n")
            f.write(self._generate_p1_actions())

            f.write("\n### P2 - 中期处理 (下月)\n")
            f.write(self._generate_p2_actions())

            # 7. 预期收益
            f.write("\n## 6. 预期收益\n\n")
            f.write(self._calculate_benefits())

        print(f"报告已生成: {report_path}")

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_split_suggestion(self, file: FileAnalysis) -> str:
        """获取拆分建议"""
        if file.total_lines > 2000:
            return "拆分为多个模块"
        elif file.class_count > 3:
            return "按类拆分"
        elif file.function_count > 20:
            return "按功能分组"
        return "提取公共函数"

    def _get_detailed_suggestion(self, file: FileAnalysis) -> str:
        """获取详细建议"""
        suggestions = []

        if file.total_lines > 2000:
            suggestions.append("文件过大，建议拆分为多个子模块")

        if file.class_count > 5:
            suggestions.append(f"包含{file.class_count}个类，建议每个类独立文件")

        if file.function_count > 30:
            suggestions.append(f"包含{file.function_count}个函数，建议按功能分组")

        # 根据文件路径给出具体建议
        if "data_source_manager" in file.filepath:
            suggestions.append("建议拆分为: 数据源基类、各数据源实现、管理器协调类")
        elif "config_service" in file.filepath:
            suggestions.append("建议拆分为: 配置加载、配置验证、配置缓存模块")
        elif "interface" in file.filepath:
            suggestions.append("建议拆分为: 数据接口基类、各类型接口实现")

        return "; ".join(suggestions) if suggestions else "保持现状"

    def _get_pattern_suggestion(self, pattern: str) -> str:
        """获取模式建议"""
        suggestions = {
            "重复的错误处理模式": "创建 @handle_errors 装饰器",
            "CRUD操作模式": "使用通用CRUD基类",
            "API调用模式": "创建 APIClient 基类",
            "缓存检查模式": "创建 @cached 装饰器",
        }
        return suggestions.get(pattern, "提取公共函数")

    def _generate_p0_actions(self) -> str:
        """生成P0行动计划"""
        actions = []

        # 超大文件
        for file in self.large_files[:5]:
            actions.append(f"- [ ] 拆分 `{file.filepath}` ({file.total_lines} 行)")

        # 最严重的重复
        for dup in self.duplicate_functions[:3]:
            actions.append(f"- [ ] 统一重复函数 `{dup.pattern}` ({len(dup.occurrences)} 处)")

        return "\n".join(actions) + "\n" if actions else "- 无P0级别问题\n"

    def _generate_p1_actions(self) -> str:
        """生成P1行动计划"""
        actions = []

        for file in self.large_files[5:10]:
            actions.append(f"- [ ] 重构 `{file.filepath}`")

        for dup in self.duplicate_functions[3:8]:
            actions.append(f"- [ ] 提取公共函数 `{dup.pattern}`")

        return "\n".join(actions) + "\n" if actions else "- 无P1级别问题\n"

    def _generate_p2_actions(self) -> str:
        """生成P2行动计划"""
        return """- [ ] 建立代码规范检查自动化
- [ ] 创建公共工具函数库
- [ ] 完善代码审查流程
- [ ] 添加复杂度监控
"""

    def _calculate_benefits(self) -> str:
        """计算预期收益"""
        total_lines_to_reduce = sum(
            f.total_lines - 800 for f in self.large_files
            if f.total_lines > 800
        )

        duplicate_functions_count = sum(
            len(dup.occurrences) - 1 for dup in self.duplicate_functions
        )

        return f"""### 代码量减少
- 通过拆分超大文件，预计可减少 **{total_lines_to_reduce}** 行代码
- 通过消除重复函数，预计可减少 **{duplicate_functions_count * 20}** 行代码
- 总计预计减少: **{total_lines_to_reduce + duplicate_functions_count * 20}** 行

### 维护性提升
- 超大文件拆分后，平均文件大小降低 **{len(self.large_files) * 30}%**
- 重复代码统一后，修改点减少 **{duplicate_functions_count}** 处
- 代码可读性显著提升

### 质量改善
- 降低代码复杂度
- 提高测试覆盖率
- 减少bug引入概率
"""


def main():
    """主函数"""
    project_path = "E:\\WorkSpace\\TradingAgents-CN"
    analyzer = CodeSimplificationAnalyzer(project_path)
    analyzer.analyze()


if __name__ == "__main__":
    main()
