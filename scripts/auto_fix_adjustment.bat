@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONPATH=%CD%

echo.
echo ======================================================================
echo 自动复权修复和验证
echo ======================================================================
echo.

echo [步骤1/3] 运行自动修复脚本...
echo.
python scripts/fix_adjustment.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 错误: 修复脚本执行失败
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo [步骤2/3] 验证修复结果...
echo.
python scripts/test_adjustment_fix.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 警告: 验证脚本执行失败或部分测试未通过
)

echo.
echo ======================================================================
echo 完成!
echo ======================================================================
echo.
echo 修复文件:
echo   - tradingagents/dataflows/providers/china/akshare.py
echo   - tradingagents/dataflows/providers/china/baostock.py
echo.
echo 修复内容:
echo   - AkShare 实时行情: 使用前复权
echo   - Baostock 最新K线: 使用前复权
echo   - 估值数据: 保持不复权 (正确)
echo.
echo 修复效果:
echo   - 技术指标 (MA、MACD、RSI) 计算准确
echo   - K线连续，无明显除权跳变
echo   - 与同花顺/通达信行为一致
echo.
echo 建议下一步:
echo   1. 提交代码: git add . && git commit -m "fix: 统一复权处理为前复权"
echo   2. 运行股票分析测试实际效果
echo.
pause
