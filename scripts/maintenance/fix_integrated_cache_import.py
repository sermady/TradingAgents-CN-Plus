# -*- coding: utf-8 -*-
"""
修复 integrated_cache 模块导入问题
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.utils.logging_init import get_logger

logger = get_logger("fix_import")


def check_and_fix_integrated_cache_import():
    """检查并修复 integrated_cache 模块导入问题"""

    logger.info("=" * 60)
    logger.info("检查 integrated_cache 模块导入")
    logger.info("=" * 60)

    # 1. 检查 cache/__init__.py
    cache_init_path = "tradingagents/dataflows/cache/__init__.py"
    try:
        with open(cache_init_path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.info(f"✅ {cache_init_path} 存在")
        logger.info(f"   内容预览: {content[:200]}...")

        # 检查是否导出 integrated
        if "integrated" not in content:
            logger.warning("⚠️ cache/__init__.py 未导出 integrated 模块")

            # 修复
            new_content = content + "\n\nfrom .integrated import IntegratedCache\n"

            with open(cache_init_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info("✅ 已添加 integrated 模块导出")
        else:
            logger.info("✅ cache/__init__.py 已导出 integrated 模块")

    except FileNotFoundError:
        logger.error(f"❌ 文件不存在: {cache_init_path}")
        return False
    except Exception as e:
        logger.error(f"❌ 读取文件失败: {e}")
        return False

    # 2. 检查 dataflows/__init__.py
    dataflows_init_path = "tradingagents/dataflows/__init__.py"
    try:
        with open(dataflows_init_path, "r", encoding="utf-8") as f:
            content = f.read()

        logger.info(f"✅ {dataflows_init_path} 存在")

        # 检查是否导出 cache 相关模块
        if "from .cache import get_cache" not in content:
            logger.warning("⚠️ dataflows/__init__.py 未导出 get_cache")

            # 修复
            new_content = content + "\n\nfrom .cache import get_cache\n"

            with open(dataflows_init_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info("✅ 已添加 get_cache 导出")
        else:
            logger.info("✅ dataflows/__init__.py 已导出 get_cache")

    except FileNotFoundError:
        logger.error(f"❌ 文件不存在: {dataflows_init_path}")
        return False
    except Exception as e:
        logger.error(f"❌ 读取文件失败: {e}")
        return False

    # 3. 测试导入
    logger.info("\n" + "=" * 60)
    logger.info("测试导入")
    logger.info("=" * 60)

    try:
        from tradingagents.dataflows.cache import get_cache

        logger.info("✅ 导入 get_cache 成功")

        # 测试调用
        cache = get_cache()
        logger.info(f"✅ get_cache() 调用成功: {type(cache)}")

        return True

    except ImportError as e:
        logger.error(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 调用失败: {e}")
        return False


if __name__ == "__main__":
    success = check_and_fix_integrated_cache_import()

    if success:
        logger.info("\n✅ 修复成功！")
        sys.exit(0)
    else:
        logger.error("\n❌ 修复失败！")
        sys.exit(1)
