# -*- coding: utf-8 -*-
"""
数据源网络连接问题诊断

诊断和解决 Tushare/AKShare/BaoStock 等数据源连接失败问题
"""

## 问题现象

多数据源同步失败，错误日志显示：

```
❌ 获取股票列表失败: ConnectionResetError(10054, '远程主机强迫关闭了一个现有的连接。')
AKShare: Failed to fetch stock list: HTTPSConnectionPool: Max retries exceeded
NameResolutionError: Failed to resolve 'query.sse.com.cn'
RuntimeError: All data sources failed to provide stock list
```

## 诊断流程

### 第一步：基础网络检查

```bash
# 1. 检查 Tushare API 连通性
ping -n 4 api.tushare.pro

# 2. 检查 DNS 解析
nslookup query.sse.com.cn
nslookup www.szse.cn

# 3. 检查代理设置
echo %HTTP_PROXY%
echo %HTTPS_PROXY%
```

### 第二步：使用 Python 诊断脚本

```python
#!/usr/bin/env python
# diagnose_network.py
import socket
import urllib.request
import ssl

def test_connection(hostname, port=443):
    """测试 TCP 连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((hostname, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"[FAIL] {hostname}:{port} - {e}")
        return False

def test_http(url):
    """测试 HTTP 连接"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[FAIL] {url} - {e}")
        return False

# 测试所有数据源
sources = [
    ("api.tushare.pro", 443, "Tushare API"),
    ("query.sse.com.cn", 443, "上交所"),
    ("www.szse.cn", 443, "深交所"),
    ("quote.eastmoney.com", 443, "东方财富"),
]

print("=" * 60)
print("数据源连接诊断")
print("=" * 60)

for hostname, port, name in sources:
    ok = test_connection(hostname, port)
    status = "✅" if ok else "❌"
    print(f"{status} {name}: {hostname}:{port}")
```

## 常见错误及解决方案

### 1. ConnectionResetError (10054)

**原因**：服务器主动断开连接

**可能原因**：
- Token 无效或过期
- 请求频率过高被限流
- 服务器临时不稳定
- 防火墙拦截

**解决方案**：

```python
# 检查 Tushare Token
python -c "
import tushare as ts
import os
from dotenv import load_dotenv
load_dotenv('app/.env')

token = os.getenv('TUSHARE_TOKEN')
if not token:
    print('❌ TUSHARE_TOKEN 未设置')
else:
    print(f'✅ Token 已设置: {token[:10]}...')
    ts.set_token(token)
    pro = ts.pro_api()
    try:
        df = pro.stock_basic(limit=5)
        print(f'✅ Token 有效，获取到 {len(df)} 条数据')
    except Exception as e:
        print(f'❌ Token 无效: {e}')
"
```

### 2. NameResolutionError (DNS 解析失败)

**原因**：无法解析域名

**解决方案**：

**方案 A：更换 DNS**
```bash
# Windows - 更改 DNS 为阿里云
netsh interface ip set dns "以太网" static 223.5.5.5
netsh interface ip add dns "以太网" 223.6.6.6 index=2

# 或腾讯 DNS
# 119.29.29.29
# 或 114 DNS
# 114.114.114.114
```

**方案 B：添加到 hosts 文件**
```
# C:\Windows\System32\drivers\etc\hosts
202.122.113.77 query.sse.com.cn
113.108.107.138 www.szse.cn
```

### 3. Max retries exceeded (连接超时)

**原因**：多次重试后仍无法连接

**可能原因**：
- 需要代理才能访问外网
- 网络不稳定
- 目标服务器不可用

**解决方案**：

**方案 A：配置代理**
```bash
# 在 app/.env 中添加
HTTP_PROXY=http://your-proxy:port
HTTPS_PROXY=http://your-proxy:port
NO_PROXY=localhost,127.0.0.1
```

**方案 B：增加超时时间**
```python
# 在适配器中增加超时
import requests

session = requests.Session()
session.timeout = (10, 60)  # (连接超时, 读取超时)
```

## 备选数据源策略

当所有网络数据源都失败时，启用本地备选：

### 1. 启用 BaoStock

```bash
# 在 .env 中启用
BAOSTOCK_UNIFIED_ENABLED=true
```

BaoStock 优势：
- 纯本地计算，不依赖外部 API
- 数据质量稳定
- 无需 Token

### 2. 使用本地股票列表缓存

```python
# 创建本地备用数据源
class LocalStockListBackup:
    """本地股票列表备用数据源"""
    
    DEFAULT_STOCKS = [
        {"code": "000001", "name": "平安银行", "ts_code": "000001.SZ"},
        {"code": "000002", "name": "万科A", "ts_code": "000002.SZ"},
        # ... 更多蓝筹股
    ]
    
    @classmethod
    def get_stock_list(cls) -> pd.DataFrame:
        """获取本地备用的股票列表"""
        return pd.DataFrame(cls.DEFAULT_STOCKS)
```

### 3. 数据源优先级配置

```bash
# 在 .env 中设置优先级
HISTORICAL_DATA_SOURCE_PRIORITY=tushare,akshare,baostock
REALTIME_DATA_SOURCE_PRIORITY=akshare,tushare

# 或启用所有备选
ENABLE_DATA_SOURCE_FALLBACK=true
```

## 网络诊断检查清单

### 基础检查
- [ ] 能访问互联网 (ping www.baidu.com)
- [ ] DNS 解析正常 (nslookup api.tushare.pro)
- [ ] 无代理或代理配置正确
- [ ] 防火墙未拦截端口 443

### 数据源特定检查
- [ ] Tushare Token 有效
- [ ] AKShare 可访问上交所/深交所/东方财富
- [ ] BaoStock 已安装并可导入

### 应用层检查
- [ ] 环境变量配置正确 (.env 文件)
- [ ] 数据源适配器初始化成功
- [ ] 降级策略已启用

## 快速修复命令

```bash
# 1. 测试所有数据源连接
python diagnose_network.py

# 2. 检查配置
cat app/.env | grep -E "TUSHARE|AKSHARE|BAOSTOCK|PROXY"

# 3. 验证 Tushare Token
python -c "import tushare as ts; ts.set_token('your-token'); pro = ts.pro_api(); print(pro.stock_basic(limit=1))"

# 4. 重启服务后重试
# 等待 10-15 分钟后再次尝试

# 5. 启用 Baostock 作为备选
export BAOSTOCK_UNIFIED_ENABLED=true
python -m app
```

## 何时使用

**触发条件**：
- 多数据源同步失败
- ConnectionResetError 或 Timeout
- DNS 解析失败
- 公司网络环境

**优先级**：
1. 检查网络连接 (ping/nslookup)
2. 验证 Token 有效性
3. 检查代理配置
4. 启用备选数据源 (Baostock)
5. 联系网络管理员

**预防措施**：
- 启用多个数据源自动降级
- 配置本地缓存机制
- 设置合理的超时和重试策略
- 监控数据源健康状态
