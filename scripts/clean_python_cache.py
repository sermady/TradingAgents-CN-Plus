#!/bin/bash
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
清理Python缓存文件脚本
"""

import os
import shutil


def clean_python_cache():
    """清理Python缓存文件"""
    print("Starting Python cache cleanup...")

    # 统计
    pycache_dirs = 0
    pyc_files = 0
    pyo_files = 0
    pytest_caches = 0

    # 遍历项目目录
    for root, dirs, files in os.walk(".", topdown=True):
        # 跳过特定目录
        dirs[:] = [
            d
            for d in dirs
            if d not in ["node_modules", "frontend", ".git", "__pycache__"]
        ]

        # 清理__pycache__目录
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            try:
                shutil.rmtree(pycache_path)
                pycache_dirs += 1
                print(f"[CLEAN] Removed {pycache_path}")
            except Exception as e:
                print(f"[ERROR] Failed to remove {pycache_path}: {e}")

        # 清理.pyc和.pyo文件
        for file in files:
            if file.endswith(".pyc"):
                pyc_file = os.path.join(root, file)
                try:
                    os.remove(pyc_file)
                    pyc_files += 1
                    print(f"[CLEAN] Removed {pyc_file}")
                except Exception as e:
                    print(f"[ERROR] Failed to remove {pyc_file}: {e}")
            elif file.endswith(".pyo"):
                pyo_file = os.path.join(root, file)
                try:
                    os.remove(pyo_file)
                    pyo_files += 1
                    print(f"[CLEAN] Removed {pyo_file}")
                except Exception as e:
                    print(f"[ERROR] Failed to remove {pyo_file}: {e}")

    # 清理.pytest_cache目录
    for root, dirs, files in os.walk(".", topdown=True):
        if ".pytest_cache" in dirs:
            pytest_path = os.path.join(root, ".pytest_cache")
            try:
                shutil.rmtree(pytest_path)
                pytest_caches += 1
                print(f"[CLEAN] Removed {pytest_path}")
            except Exception as e:
                print(f"[ERROR] Failed to remove {pytest_path}: {e}")

    # 打印统计
    print("\n" + "=" * 50)
    print("Python Cache Cleanup Summary")
    print("=" * 50)
    print(f"__pycache__ directories removed: {pycache_dirs}")
    print(f".pyc files removed: {pyc_files}")
    print(f".pyo files removed: {pyo_files}")
    print(f".pytest_cache directories removed: {pytest_caches}")
    print("=" * 50)
    print(
        f"Total items cleaned: {pycache_dirs + pyc_files + pyo_files + pytest_caches}"
    )
    print("[SUCCESS] Cache cleanup completed!")


if __name__ == "__main__":
    clean_python_cache()
