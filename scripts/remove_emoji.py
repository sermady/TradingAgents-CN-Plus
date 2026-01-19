# -*- coding: utf-8 -*-
"""Remove emoji from test script"""

import re

file_path = "scripts/test_adjustment_fix.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 移除所有emoji
content = re.sub(r"[\U0001F300-\U0001F64F]", "", content)
content = re.sub(r"[\U0001F680-\U0001F6FF]", "", content)
content = re.sub(r"[\U00002702-\U000027B0]", "", content)
content = re.sub(r"[\U000024C2-\U0001F251]", "", content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("OK: Emoji removed from test_adjustment_fix.py")
