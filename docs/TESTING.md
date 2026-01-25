# TradingAgents-CN 测试文档

## 📋 测试概览

本测试套件为 TradingAgents-CN 项目提供全面的测试覆盖，包括单元测试、集成测试和端到端测试。

### 测试覆盖率目标

- **单元测试**: 覆盖核心业务逻辑
- **集成测试**: 覆盖 API 端点和服务集成
- **E2E 测试**: 覆盖完整用户工作流程

### 测试统计

| 类型 | 文件数 | 测试数量（估算） |
|------|--------|------------------|
| 单元测试 | 19+ | 400+ |
| 集成测试 | 4+ | 60+ |
| E2E 测试 | 1+ | 10+ |
| **总计** | **24+** | **470+** |

---

## 🚀 快速开始

### 前置要求

```bash
# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov pytest-xdist httpx

# 可选：性能测试
pip install pytest-benchmark
```

### 运行所有测试

```bash
# 运行所有测试
pytest

# 运行单元测试（快速）
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行 E2E 测试
pytest tests/e2e/ -v
```

---

## 📂 测试目录结构

```
tests/
├── conftest.py                    # 全局 pytest 配置和 fixtures
├── fixtures/                      # 共享 fixtures
│   ├── __init__.py
│   ├── database.py               # MongoDB fixtures
│   ├── redis.py                  # Redis fixtures
│   ├── auth.py                   # 认证 fixtures
│   ├── stock_data.py             # 股票数据 fixtures
│   ├── llm.py                    # LLM mock fixtures
│   └── sample_data.py            # 通用测试数据
│
├── unit/                          # 单元测试
│   ├── services/                 # 服务层测试
│   │   ├── test_analysis_service.py
│   │   ├── test_auth_service.py
│   │   ├── test_database_service.py
│   │   ├── test_unified_cache_service.py
│   │   ├── test_quotes_service.py
│   │   ├── test_screening_service.py
│   │   ├── test_favorites_service.py
│   │   └── test_progress_manager.py
│   │
│   ├── agents/                   # Agent 系统测试
│   │   ├── test_market_analyst.py
│   │   ├── test_fundamentals_analyst.py
│   │   ├── test_news_analyst.py
│   │   ├── test_social_media_analyst.py
│   │   ├── test_researchers.py
│   │   ├── test_trader.py
│   │   ├── test_trading_graph.py
│   │   ├── test_parallel_analysts.py
│   │   ├── test_signal_processing.py
│   │   ├── test_conditional_logic.py
│   │   └── test_reflection.py
│   │
│   ├── llm_adapters/            # LLM 适配器测试
│   │   └── test_llm_adapters.py
│   │
│   └── dataflows/               # 数据流测试
│       └── test_data_providers.py
│
├── integration/                  # 集成测试
│   ├── test_health_api.py
│   ├── test_auth_api.py
│   ├── test_stocks_api.py
│   ├── test_analysis_api.py
│   ├── test_screening_api.py
│   └── test_favorites_api.py
│
├── e2e/                         # 端到端测试
│   └── test_complete_workflows.py
│
└── legacy/                      # 遗留测试（已忽略）
    └── ...
```

---

## 🏷️ 测试标记

使用标记来选择性运行测试：

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 只运行 E2E 测试
pytest -m e2e

# 跳过慢速测试
pytest -m "not slow"

# 运行需要认证的测试
pytest -m requires_auth

# 运行需要数据库的测试
pytest -m requires_db
```

### 可用标记

- `@pytest.mark.unit`: 单元测试（快速，不依赖外部服务）
- `@pytest.mark.integration`: 集成测试（需要数据库/API）
- `@pytest.mark.e2e`: 端到端测试（完整用户流程）
- `@pytest.mark.slow`: 慢速测试（运行时间较长）
- `@pytest.mark.requires_auth`: 需要认证的测试
- `@pytest.mark.requires_db`: 需要数据库的测试
- `@pytest.mark.requires_redis`: 需要 Redis 的测试

---

## 🔧 环境配置

### 测试环境变量

创建 `.env.test` 文件：

```bash
# 数据库配置（使用测试数据库）
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DATABASE=tradingagents_test

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=15  # 使用独立的测试数据库

# LLM API 密钥（可选，用于真实 API 测试）
# 如果未配置，将使用 mock
DASHSCOPE_API_KEY=your_test_key
GOOGLE_API_KEY=your_test_key
DEEPSEEK_API_KEY=your_test_key

# 数据源密钥（可选）
TUSHARE_TOKEN=your_test_token
FINNHUB_API_KEY=your_test_key

# 测试配置
TESTING=true
DEBUG=false
```

### 启动测试环境

```bash
# 使用 Docker 启动 MongoDB 和 Redis
docker-compose -f docker-compose.yml up -d mongodb redis

# 或使用开发脚本
scripts/docker/start_docker_services.bat  # Windows
scripts/docker/start_docker_services.sh  # Linux/Mac
```

---

## 📊 测试覆盖率

### 生成覆盖率报告

```bash
# 安装 coverage 工具
pip install pytest-cov

# 运行测试并生成覆盖率报告
pytest --cov=tradingagents --cov=app --cov-report=term-missing

# 生成 HTML 覆盖率报告
pytest --cov=tradingagents --cov=app --cov-report=html
open htmlcov/index.html
```

### 覆盖率目标

- **核心业务逻辑**: 90%+
- **API 端点**: 85%+
- **服务层**: 80%+
- **整体覆盖率**: 80%+

---

## ⚡ 性能测试

### 使用 pytest-benchmark

```bash
# 安装
pip install pytest-benchmark

# 运行性能测试
pytest --benchmark-only

# 运行特定性能测试
pytest tests/unit/services/test_database_service.py -k test_find_performance --benchmark-only
```

---

## 🔍 调试测试

### 单个测试

```bash
# 运行单个测试
pytest tests/unit/services/test_auth_service.py::TestAuthService::test_hash_password -v

# 进入调试模式
pytest tests/unit/services/test_auth_service.py::TestAuthService::test_hash_password -s

# 显示详细输出
pytest tests/unit/services/test_auth_service.py -vv
```

### 失败测试

```bash
# 只运行上次失败的测试
pytest --lf

# 先运行失败的测试，然后运行其余的
pytest --ff

# 停止在第一个失败的测试
pytest -x

# 显示详细的错误信息
pytest --tb=long
```

---

## 📝 编写新测试

### 单元测试模板

```python
# -*- coding: utf-8 -*-
"""
模块测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

# 测试标记
pytestmark = pytest.mark.unit


class TestModuleName:
    """模块测试"""

    @pytest.fixture
    def setup_data(self):
        """测试数据 fixture"""
        return {
            "key1": "value1",
            "key2": "value2"
        }

    @pytest.mark.asyncio
    async def test_function_success(self, setup_data):
        """测试函数 - 成功场景"""
        # Arrange
        input_data = setup_data

        # Act
        result = await your_function(input_data)

        # Assert
        assert result is not None
        assert result["expected_key"] == "expected_value"

    @pytest.mark.asyncio
    async def test_function_error(self):
        """测试函数 - 错误场景"""
        # Arrange
        invalid_input = None

        # Act & Assert
        with pytest.raises(ValueError):
            await your_function(invalid_input)
```

### 集成测试模板

```python
# -*- coding: utf-8 -*-
"""
API 集成测试
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestYourAPI:
    """API 测试"""

    @pytest.mark.asyncio
    async def test_endpoint_success(
        self,
        async_client: AsyncClient,
        test_user_headers: dict
    ):
        """测试端点 - 成功场景"""
        response = await async_client.post(
            "/api/endpoint",
            headers=test_user_headers,
            json={"data": "test"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data

    @pytest.mark.asyncio
    async def test_endpoint_unauthorized(self, async_client: AsyncClient):
        """测试端点 - 未授权"""
        response = await async_client.post(
            "/api/endpoint",
            json={"data": "test"}
        )

        assert response.status_code == 401
```

---

## 🐛 常见问题

### 测试失败

1. **数据库连接失败**
   ```bash
   # 确保 MongoDB 和 Redis 正在运行
   docker-compose ps

   # 检查连接配置
   cat .env.test
   ```

2. **LLM API 密钥未配置**
   ```bash
   # 大多数测试使用 mock，不需要真实密钥
   # 如果需要真实 API 测试，配置 .env.test
   echo "DASHSCOPE_API_KEY=your_key" >> .env.test
   ```

3. **端口被占用**
   ```bash
   # 检查端口占用
   netstat -ano | findstr :8000  # Windows
   lsof -i :8000  # Linux/Mac

   # 修改测试端口
   export PORT=8001
   ```

### 速度优化

```bash
# 使用并行测试（需要 pytest-xdist）
pip install pytest-xdist
pytest -n auto  # 自动检测 CPU 核心数

# 只运行快速测试
pytest -m "not slow"

# 跳过 E2E 测试
pytest -m "not e2e"
```

---

## 📚 参考资料

- [Pytest 文档](https://docs.pytest.org/)
- [pytest-asyncio 文档](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov 文档](https://pytest-cov.readthedocs.io/)
- [FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)

---

## 🤝 贡献指南

### 添加新测试

1. 确定测试类型（单元/集成/E2E）
2. 创建对应的测试文件
3. 遵循命名规范 `test_<module>.py`
4. 添加适当的测试标记
5. 编写清晰的测试文档字符串
6. 确保测试独立且可重复运行

### 测试最佳实践

- ✅ 每个测试只验证一个功能点
- ✅ 使用描述性的测试名称
- ✅ Arrange-Act-Assert 模式
- ✅ 使用 fixtures 管理测试数据
- ✅ 清理测试后的资源
- ❌ 避免测试之间的依赖
- ❌ 不要硬编码测试数据
- ❌ 不要在生产数据上运行测试

---

## 📈 持续集成

测试将在每次提交时自动运行：

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: pytest --cov=tradingagents --cov=app
```

---

**最后更新**: 2026-01-25
