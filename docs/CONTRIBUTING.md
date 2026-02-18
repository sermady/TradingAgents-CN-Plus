# 开发贡献指南

**生成日期**: 2026-02-18
**来源**: package.json, pyproject.toml, .env.example

---

## 目录

1. [开发环境配置](#开发环境配置)
2. [可用脚本](#可用脚本)
3. [开发工作流](#开发工作流)
4. [测试程序](#测试程序)
5. [项目结构](#项目结构)
6. [环境变量配置](#环境变量配置)

---

## 开发环境配置

### 系统要求

- **Python**: >= 3.10
- **Node.js**: >= 18.0.0
- **npm**: >= 8.0.0
- **MongoDB**: >= 4.4
- **Redis**: >= 6.2

### 后端环境配置

```bash
# 1. 克隆仓库
git clone <repository-url>
cd TradingAgents-CN

# 2. 创建虚拟环境
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. 安装依赖
pip install -e .

# 或使用 uv (更快)
uv pip install -e .
```

### 前端环境配置

```bash
cd frontend

# 使用 yarn (推荐)
yarn install

# 或使用 npm
npm install
```

### 环境变量设置

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入必需的配置
# 必需: MongoDB, Redis, JWT_SECRET, CSRF_SECRET
```

**必需配置项**:

| 变量 | 说明 | 获取方式 |
|-----|------|---------|
| `MONGODB_HOST` | MongoDB 主机 | 本地安装或使用云托管 |
| `REDIS_HOST` | Redis 主机 | 本地安装或使用云托管 |
| `JWT_SECRET` | JWT 签名密钥 | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `CSRF_SECRET` | CSRF 保护密钥 | 同上 |

**推荐配置项**:

| 变量 | 说明 | 获取地址 |
|-----|------|---------|
| `DEEPSEEK_API_KEY` | DeepSeek API | https://platform.deepseek.com/ |
| `DASHSCOPE_API_KEY` | 阿里百炼 API | https://dashscope.aliyun.com/ |
| `TUSHARE_TOKEN` | Tushare 数据 | https://tushare.pro/ |

---

## 可用脚本

### 后端脚本

| 脚本 | 命令 | 说明 |
|-----|------|------|
| 启动后端 | `python -m app` | 启动 FastAPI 服务 |
| 安装依赖 | `pip install -e .` | 安装项目依赖 |
| 运行测试 | `python -m pytest` | 运行所有测试 |
| 语法检查 | `python -m py_compile <file>` | 检查 Python 语法 |

### 前端脚本 (package.json)

| 脚本 | 命令 | 说明 |
|-----|------|------|
| 开发服务器 | `yarn dev` / `npm run dev` | 启动 Vite 开发服务器 |
| 生产构建 | `yarn build` / `npm run build` | 构建生产版本 |
| 代码检查 | `yarn lint` / `npm run lint` | ESLint 检查并修复 |
| 代码格式化 | `yarn format` / `npm run format` | Prettier 格式化 |
| 类型检查 | `yarn type-check` / `npm run type-check` | Vue TypeScript 检查 |
| 预览 | `yarn preview` / `npm run preview` | 预览生产构建 |

### 数据导入脚本

```bash
# 使用 Baostock 导入 A 股数据
python scripts/import/import_a_stocks_unified.py --data-source baostock

# 使用 Tushare 导入
python scripts/import/import_a_stocks_unified.py --data-source tushare

# 自动选择最佳数据源
python scripts/import/import_a_stocks_unified.py --data-source auto
```

### 测试脚本

```bash
# 运行所有测试
python -m pytest

# 仅运行单元测试
python -m pytest -m unit -v

# 运行集成测试
python -m pytest -m integration -v

# 运行特定测试文件
python -m pytest tests/unit/test_data_manager.py -v

# 运行覆盖率检查
python -m pytest --cov=tradingagents --cov=app --cov-report=term-missing
```

---

## 开发工作流

### 1. 功能开发流程

```
1. 创建功能分支
   git checkout -b feature/your-feature-name

2. 开发并测试
   - 编写代码
   - 运行本地测试
   - 确保类型检查通过

3. 提交代码
   git add .
   git commit -m "feat: 描述你的功能"

4. 推送到远程
   git push origin feature/your-feature-name

5. 创建 Pull Request
```

### 2. 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范:

```
<type>: <description>

[optional body]
```

**类型说明**:

| 类型 | 用途 |
|-----|------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `refactor` | 代码重构 |
| `perf` | 性能优化 |
| `docs` | 文档更新 |
| `test` | 测试相关 |
| `chore` | 构建/工具链 |
| `ci` | CI/CD 配置 |

**示例**:

```bash
git commit -m "feat: 添加 Baostock 数据源支持"
git commit -m "fix: 修复统一导入器编码问题"
git commit -m "refactor: 重构数据流架构"
git commit -m "docs: 更新开发指南"
```

### 3. 代码质量检查

提交前必须检查:

```bash
# Python 语法检查
python -m py_compile your_file.py

# 前端代码检查
cd frontend && yarn lint

# 类型检查
cd frontend && yarn type-check

# 运行测试
python -m pytest -m unit
```

---

## 测试程序

### 测试分类

| 标记 | 说明 | 运行命令 |
|-----|------|---------|
| `unit` | 单元测试（快速，无外部依赖） | `pytest -m unit` |
| `integration` | 集成测试（需要数据库/API） | `pytest -m integration` |
| `slow` | 慢测试 | `pytest -m slow` |
| `requires_db` | 需要数据库 | `pytest -m requires_db` |

### 测试目录结构

```
tests/
├── unit/               # 单元测试
├── integration/        # 集成测试
├── e2e/               # 端到端测试
└── fixtures/          # 测试数据
```

### 编写测试示例

```python
import pytest

@pytest.mark.unit
def test_calculate_pe_ratio():
    """测试 PE 比率计算"""
    result = calculate_pe_ratio(price=100, eps=10)
    assert result == 10.0

@pytest.mark.integration
@pytest.mark.requires_db
async def test_mongodb_connection():
    """测试 MongoDB 连接"""
    client = await get_mongodb_client()
    assert client is not None
```

---

## 项目结构

```
TradingAgents-CN/
├── app/                          # FastAPI 后端
│   ├── core/                    # 核心配置
│   ├── models/                  # 数据模型
│   ├── routers/                 # API 路由
│   ├── services/                # 业务服务
│   └── worker/                  # 后台任务
├── frontend/                     # Vue 3 前端
│   ├── src/
│   │   ├── components/         # 组件
│   │   ├── views/              # 页面
│   │   ├── stores/             # Pinia 状态
│   │   └── api/                # API 调用
│   └── package.json
├── tradingagents/               # 核心分析引擎
│   ├── agents/                 # AI Agent
│   ├── dataflows/              # 数据流
│   ├── graph/                  # LangGraph
│   └── llm_adapters/           # LLM 适配器
├── scripts/                     # 工具脚本
│   ├── import/                 # 数据导入
│   ├── test/                   # 测试脚本
│   └── validation/             # 验证脚本
├── docs/                        # 文档
├── tests/                       # 测试代码
├── pyproject.toml              # Python 配置
└── .env.example                # 环境变量示例
```

---

## 环境变量配置

### 必需配置

```env
# 数据库
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=your_password
MONGODB_DATABASE=tradingagents
MONGODB_AUTH_SOURCE=admin

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password

# 安全
JWT_SECRET=your-secret-key
CSRF_SECRET=your-csrf-secret
```

### API 密钥配置

```env
# 大模型 API (至少配置一个)
DEEPSEEK_API_KEY=your_key
DASHSCOPE_API_KEY=your_key

# 数据源 API
TUSHARE_TOKEN=your_token
FINNHUB_API_KEY=your_key
```

### 代理配置

```env
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
NO_PROXY=localhost,127.0.0.1,eastmoney.com,api.tushare.pro
```

---

## 常见问题

### 1. 安装依赖失败

```bash
# 升级 pip
python -m pip install --upgrade pip

# 使用镜像源
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. 前端构建失败

```bash
# 清除缓存
cd frontend
rm -rf node_modules
yarn install
```

### 3. 测试失败

```bash
# 确保 MongoDB 和 Redis 已启动
# 检查 .env 配置是否正确
```

---

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - AI 助手指引
- [RUNBOOK.md](./RUNBOOK.md) - 部署和运维指南
- [配置指南](./configuration_guide.md) - 详细配置说明

---

**最后更新**: 2026-02-18
