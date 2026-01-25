file_path = 'E:/WorkSpace/TradingAgents-CN/tradingagents/dataflows/data_source_manager.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复逻辑
old = '''            if boll_position >= 100:
                result += " (接近上轨，可能超买 ⚠️)\n\n"
            elif boll_position >= 80 -and boll_position < 100:
                result += " (接近下轨，可能超卖 ⚠️)\n\n"
            else:
                result += " (中性区域)\n\n"'''

new = '''            if boll_position >= 100:
                result += " (已突破上轨，多头确认信号！🔴)\n\n"
            elif boll_position >= 80:
                result += " (接近上轨，可能超买 ⚠️)\n\n"
            elif boll_position <= 20:
                result += " (接近下轨，可能超卖 ⚠️)\n\n"
            else:
                result += " (中性区域)\n\n"'''

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Fix complete!')
else:
    print('Pattern not found')
