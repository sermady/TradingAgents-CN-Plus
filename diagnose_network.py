#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

"""
网络连接诊断工具
测试 Tushare 和 AKShare 的数据源连接
"""

import socket
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse
import ssl


def test_dns_resolution(hostname, description=""):
    """测试 DNS 解析"""
    print(f"\n[DNS 测试] {description or hostname}")
    print("-" * 60)
    try:
        # 获取 IPv4 地址
        ipv4_addrs = socket.getaddrinfo(hostname, None, socket.AF_INET)
        print(f"✅ IPv4 解析成功:")
        for addr in set([x[4][0] for x in ipv4_addrs]):
            print(f"   {addr}")

        # 尝试获取 IPv6 地址
        try:
            ipv6_addrs = socket.getaddrinfo(hostname, None, socket.AF_INET6)
            print(f"✅ IPv6 解析成功:")
            for addr in set([x[4][0] for x in ipv6_addrs]):
                print(f"   {addr}")
        except socket.gaierror:
            print(f"⚠️ IPv6 解析失败（可能网络不支持 IPv6）")

        return True
    except socket.gaierror as e:
        print(f"❌ DNS 解析失败: {e}")
        return False


def test_tcp_connection(hostname, port, timeout=10):
    """测试 TCP 连接"""
    print(f"\n[TCP 测试] {hostname}:{port}")
    print("-" * 60)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((hostname, port))
        if result == 0:
            print(f"✅ 端口 {port} 连接成功")
            sock.close()
            return True
        else:
            print(f"❌ 端口 {port} 连接失败 (错误码: {result})")
            return False
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return False


def test_http_connection(url, description="", timeout=10):
    """测试 HTTP/HTTPS 连接"""
    print(f"\n[HTTP 测试] {description or url}")
    print("-" * 60)

    # 创建 SSL 上下文，允许我们查看证书信息
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            elapsed = time.time() - start_time
            print(f"✅ HTTP 连接成功")
            print(f"   状态码: {response.status}")
            print(f"   响应时间: {elapsed:.2f}s")
            print(f"   内容长度: {len(response.read())} bytes")
            return True
    except urllib.error.URLError as e:
        print(f"❌ HTTP 连接失败: {e}")
        if hasattr(e, "code"):
            print(f"   HTTP 错误码: {e.code}")
        if hasattr(e, "reason"):
            print(f"   原因: {e.reason}")
        return False
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        return False


def test_tushare_api():
    """测试 Tushare API"""
    print("\n" + "=" * 60)
    print("测试 Tushare API 连接")
    print("=" * 60)

    # Tushare API 地址
    return test_http_connection("https://api.tushare.pro", "Tushare API")


def test_akshare_sources():
    """测试 AKShare 需要的数据源"""
    print("\n" + "=" * 60)
    print("测试 AKShare 数据源连接")
    print("=" * 60)

    sources = [
        ("query.sse.com.cn", 443, "上交所查询接口"),
        ("www.szse.cn", 443, "深交所官网"),
        ("quote.eastmoney.com", 443, "东方财富行情"),
        ("push2.eastmoney.com", 443, "东方财富推送服务"),
        ("datacenter-web.eastmoney.com", 443, "东方财富数据中心"),
    ]

    results = []
    for hostname, port, desc in sources:
        # 先测试 DNS
        dns_ok = test_dns_resolution(hostname, desc)

        # 再测试 TCP 连接
        tcp_ok = test_tcp_connection(hostname, port)

        results.append((desc, dns_ok, tcp_ok))

    return results


def diagnose_network():
    """完整的网络诊断"""
    print("=" * 60)
    print("网络连接诊断报告")
    print("=" * 60)
    print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python 版本: {sys.version}")

    # 检查代理设置
    import os

    print("\n" + "-" * 60)
    print("代理设置检查")
    print("-" * 60)
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")

    if http_proxy:
        print(f"HTTP_PROXY: {http_proxy}")
    else:
        print("HTTP_PROXY: 未设置")

    if https_proxy:
        print(f"HTTPS_PROXY: {https_proxy}")
    else:
        print("HTTPS_PROXY: 未设置")

    if no_proxy:
        print(f"NO_PROXY: {no_proxy}")
    else:
        print("NO_PROXY: 未设置")

    # 测试 Tushare
    tushare_ok = test_tushare_api()

    # 测试 AKShare 数据源
    akshare_results = test_akshare_sources()

    # 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)

    if tushare_ok:
        print("✅ Tushare API: 可连接")
    else:
        print("❌ Tushare API: 无法连接")

    failed_sources = [desc for desc, dns, tcp in akshare_results if not (dns and tcp)]
    if failed_sources:
        print(f"❌ AKShare 数据源问题 ({len(failed_sources)} 个失败):")
        for source in failed_sources:
            print(f"   - {source}")
    else:
        print("✅ AKShare 数据源: 全部可连接")

    # 建议
    print("\n" + "=" * 60)
    print("修复建议")
    print("=" * 60)

    if not tushare_ok or failed_sources:
        print("\n检测到网络连接问题，请尝试以下方案：")
        print("\n1. 检查网络连接是否正常")
        print("   - 确认可以访问互联网")
        print("   - 尝试访问 https://api.tushare.pro 和 https://www.szse.cn")

        print("\n2. 如果是公司网络，可能需要配置代理：")
        print("   在 .env 文件中添加：")
        print("   HTTP_PROXY=http://your-proxy:port")
        print("   HTTPS_PROXY=http://your-proxy:port")

        print("\n3. 如果 DNS 解析失败，尝试更换 DNS：")
        print("   - 阿里云 DNS: 223.5.5.5, 223.6.6.6")
        print("   - 腾讯 DNS: 119.29.29.29")
        print("   - 114 DNS: 114.114.114.114")

        print("\n4. 如果问题持续，建议启用 Baostock 作为备选：")
        print("   在 .env 文件中添加：")
        print("   BAOSTOCK_UNIFIED_ENABLED=true")
    else:
        print("✅ 所有网络连接测试通过！")
        print("\n如果仍然无法获取数据，可能是：")
        print("- Tushare 需要有效的 token")
        print("- 服务器临时不可用")
        print("- 请求频率限制")


if __name__ == "__main__":
    diagnose_network()
