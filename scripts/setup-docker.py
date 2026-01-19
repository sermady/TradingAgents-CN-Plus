#!/usr/bin/env python3
"""
TradingAgents-CN Docker 环境配置脚本
前后端分离架构 (FastAPI + Vue3)
版本: v1.0.0-preview

帮助用户快速配置 Docker 部署环境
"""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


# 颜色输出支持
class Colors:
    """终端颜色"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

    @staticmethod
    def is_supported():
        """检查是否支持颜色输出"""
        if os.name == 'nt':
            # Windows 10+ 支持 ANSI 颜色
            return os.environ.get('TERM') or os.environ.get('WT_SESSION')
        return True


def print_color(msg: str, color: str = Colors.NC):
    """带颜色打印"""
    if Colors.is_supported():
        print(f"{color}{msg}{Colors.NC}")
    else:
        # 移除颜色代码
        print(msg)


def print_banner():
    """打印启动横幅"""
    print_color("=" * 50, Colors.CYAN)
    print_color("🐳 TradingAgents-CN Docker 环境配置向导", Colors.GREEN)
    print_color("=" * 50, Colors.CYAN)
    print_color("架构: FastAPI 后端 + Vue3 前端", Colors.CYAN)
    print_color("版本: v1.0.0-preview", Colors.CYAN)
    print()


def check_docker() -> bool:
    """检查 Docker 环境"""
    print_color("🔍 检查 Docker 环境...", Colors.YELLOW)

    # 检查 Docker
    if shutil.which('docker') is None:
        print_color("❌ 未找到 Docker，请先安装 Docker Desktop", Colors.RED)
        print()
        print_color("💡 安装指南:", Colors.CYAN)
        print("   - Windows/macOS: https://www.docker.com/products/docker-desktop")
        print("   - Linux: https://docs.docker.com/engine/install/")
        return False

    # 检查 Docker 是否运行
    try:
        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            print_color("❌ Docker 未运行，请启动 Docker Desktop", Colors.RED)
            return False
    except subprocess.TimeoutExpired:
        print_color("❌ Docker 响应超时，请检查 Docker 状态", Colors.RED)
        return False
    except Exception as e:
        print_color(f"❌ Docker 检查失败: {e}", Colors.RED)
        return False

    print_color("✅ Docker 运行正常", Colors.GREEN)

    # 检查 docker-compose
    compose_available = False
    compose_cmd = None

    if shutil.which('docker-compose') is not None:
        compose_available = True
        compose_cmd = 'docker-compose'
    else:
        # 尝试新版 docker compose
        try:
            result = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                compose_available = True
                compose_cmd = 'docker compose'
        except:
            pass

    if not compose_available:
        print_color("❌ 未找到 docker-compose，请确保 Docker Desktop 已正确安装", Colors.RED)
        return False

    print_color(f"✅ 使用: {compose_cmd}", Colors.GREEN)
    return True


def setup_directories(project_root: Path) -> bool:
    """创建必要的目录"""
    print()
    print_color("📁 创建必要目录...", Colors.YELLOW)

    directories = ['logs', 'data', 'config']

    for dir_name in directories:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   📁 创建目录: {dir_name}")
        else:
            print(f"   📁 目录已存在: {dir_name}")

    # 创建 .gitkeep 文件
    gitkeep_file = project_root / 'logs' / '.gitkeep'
    if not gitkeep_file.exists():
        gitkeep_file.touch()

    print_color("✅ 目录准备完成", Colors.GREEN)
    return True


def setup_env_file(project_root: Path) -> bool:
    """配置 .env 文件"""
    print()
    print_color("🔧 配置环境变量...", Colors.YELLOW)

    env_file = project_root / ".env"
    env_docker = project_root / ".env.docker"
    env_example = project_root / ".env.example"

    # 检查 .env 文件是否存在
    if env_file.exists():
        print_color("📁 发现现有的 .env 文件", Colors.CYAN)
        choice = input("是否要备份现有配置并重新配置？(y/N): ").lower().strip()
        if choice == 'y':
            backup_file = project_root / f".env.backup.{int(time.time())}"
            shutil.copy(env_file, backup_file)
            print_color(f"✅ 已备份到: {backup_file.name}", Colors.GREEN)
        else:
            print_color("⏭️ 保留现有配置", Colors.CYAN)
            return True

    # 选择配置模板
    if env_docker.exists():
        print_color("📋 使用 Docker 专用配置模板 (.env.docker)", Colors.CYAN)
        shutil.copy(env_docker, env_file)
        print_color("✅ 已复制 Docker 配置", Colors.GREEN)
    elif env_example.exists():
        print_color("📋 使用示例配置模板 (.env.example)", Colors.CYAN)
        shutil.copy(env_example, env_file)

        # 修改为 Docker 环境配置
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Docker 环境配置
            docker_configs = {
                'TRADINGAGENTS_MONGODB_URL': 'mongodb://admin:tradingagents123@mongodb:27017/tradingagents?authSource=admin',
                'TRADINGAGENTS_REDIS_URL': 'redis://:tradingagents123@redis:6379',
                'TRADINGAGENTS_CACHE_TYPE': 'redis',
                'DOCKER_CONTAINER': 'true',
            }

            for key, value in docker_configs.items():
                pattern = f'^{key}=.*$'
                replacement = f'{key}={value}'
                if re.search(pattern, content, re.MULTILINE):
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                else:
                    content += f"\n{key}={value}"

            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print_color("✅ Docker 环境变量已配置", Colors.GREEN)
        except Exception as e:
            print_color(f"⚠️ 配置修改失败: {e}", Colors.YELLOW)
    else:
        print_color("❌ 找不到配置模板文件 (.env.docker 或 .env.example)", Colors.RED)
        return False

    return True


def show_api_key_reminder():
    """显示 API 密钥配置提醒"""
    print()
    print_color("🔑 API 密钥配置", Colors.YELLOW)
    print_color("请编辑 .env 文件，配置以下 API 密钥（至少配置一个 LLM）：", Colors.CYAN)
    print()
    print("   LLM 服务（必须至少配置一个）:")
    print("   - TRADINGAGENTS_DEEPSEEK_API_KEY    (DeepSeek，推荐)")
    print("   - TRADINGAGENTS_DASHSCOPE_API_KEY   (阿里云通义千问)")
    print("   - TRADINGAGENTS_OPENAI_API_KEY      (OpenAI)")
    print()
    print("   数据源（可选，但推荐配置）:")
    print("   - TRADINGAGENTS_TUSHARE_TOKEN       (Tushare 数据)")
    print("   - TRADINGAGENTS_FINNHUB_API_KEY     (美股数据)")
    print()


def show_next_steps():
    """显示下一步操作"""
    print()
    print_color("=" * 50, Colors.GREEN)
    print_color("🚀 下一步操作", Colors.GREEN)
    print_color("=" * 50, Colors.GREEN)
    print()
    print_color("1. 编辑 .env 文件，填入您的 API 密钥", Colors.CYAN)
    print("   Windows: notepad .env")
    print("   Linux/Mac: nano .env")
    print()
    print_color("2. 启动 Docker 服务", Colors.CYAN)
    print("   docker-compose up -d")
    print()
    print_color("3. 访问应用", Colors.CYAN)
    print("   前端界面: http://localhost:3000")
    print("   后端API:  http://localhost:8000")
    print("   API文档:  http://localhost:8000/docs")
    print()
    print_color("4. 查看日志", Colors.CYAN)
    print("   docker-compose logs -f backend")
    print("   docker-compose logs -f frontend")
    print()
    print_color("5. 停止服务", Colors.CYAN)
    print("   docker-compose down")
    print()
    print_color("💡 可选：启用管理界面", Colors.YELLOW)
    print("   docker-compose --profile management up -d")
    print("   Redis 管理: http://localhost:8081")
    print("   Mongo 管理: http://localhost:8082")
    print()


def show_troubleshooting():
    """显示常见问题解决方案"""
    print_color("📚 常见问题", Colors.YELLOW)
    print()
    print("Q: 容器启动失败？")
    print("A: 检查端口是否被占用: 3000, 8000, 27017, 6379")
    print("   Windows: netstat -ano | findstr :3000")
    print("   Linux: lsof -i :3000")
    print()
    print("Q: 数据库连接失败？")
    print("A: 等待数据库完全启动后再访问应用")
    print("   docker-compose logs mongodb")
    print()
    print("Q: 如何查看完整日志？")
    print("A: docker-compose logs -f --tail=100")
    print()


def main():
    """主函数"""
    print_banner()

    # 获取项目根目录
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent

    # 切换到项目根目录
    os.chdir(project_root)
    print(f"📂 项目目录: {project_root}")
    print()

    # 检查 Docker 环境
    if not check_docker():
        print()
        print_color("❌ Docker 环境检查失败，请先解决上述问题", Colors.RED)
        sys.exit(1)

    # 创建必要目录
    if not setup_directories(project_root):
        print_color("❌ 目录创建失败", Colors.RED)
        sys.exit(1)

    # 配置环境变量
    if not setup_env_file(project_root):
        print_color("❌ 环境变量配置失败", Colors.RED)
        sys.exit(1)

    # 显示 API 密钥提醒
    show_api_key_reminder()

    # 显示下一步操作
    show_next_steps()

    # 询问是否立即启动
    print()
    choice = input("是否立即启动 Docker 服务？(Y/n): ").lower().strip()
    if choice != 'n':
        print()
        print_color("🐳 正在启动 Docker 服务...", Colors.YELLOW)
        print()

        try:
            # 尝试使用 docker-compose
            if shutil.which('docker-compose'):
                subprocess.run(['docker-compose', 'up', '-d'], check=True)
            else:
                subprocess.run(['docker', 'compose', 'up', '-d'], check=True)

            print()
            print_color("✅ Docker 服务启动成功！", Colors.GREEN)
            print()
            print_color("🌐 访问地址:", Colors.CYAN)
            print("   前端界面: http://localhost:3000")
            print("   后端API:  http://localhost:8000")
            print("   API文档:  http://localhost:8000/docs")
            print()
            print_color("⏳ 首次启动可能需要几分钟来拉取镜像和初始化数据库...", Colors.YELLOW)
            print_color("   使用 'docker-compose logs -f' 查看启动进度", Colors.CYAN)
        except subprocess.CalledProcessError as e:
            print_color(f"❌ Docker 服务启动失败: {e}", Colors.RED)
            print_color("请检查 Docker 日志: docker-compose logs", Colors.YELLOW)
            sys.exit(1)
    else:
        print()
        print_color("⏭️ 跳过启动，您可以稍后手动运行: docker-compose up -d", Colors.CYAN)

    print()
    show_troubleshooting()

    print_color("🎉 配置完成！", Colors.GREEN)
    print()


if __name__ == "__main__":
    main()
