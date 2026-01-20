# -*- coding: utf-8 -*-
from fastapi import APIRouter
import time
from pathlib import Path

router = APIRouter()


def get_version() -> str:
    """从 VERSION 文件读取版本号"""
    try:
        version_file = Path(__file__).parent.parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text(encoding='utf-8').strip()
    except Exception:
        pass
    return "0.1.16"  # 默认版本号


@router.get("/health")
async def health():
    """
    轻量级健康检查 - 不查数据库
    用于容器健康检查和负载均衡器探测
    """
    return {
        "success": True,
        "data": {
            "status": "ok",
            "timestamp": int(time.time())
        }
    }

@router.get("/health/detailed")
async def health_detailed():
    """
    深度健康检查 - 包含数据库和服务状态
    用于监控系统和服务诊断
    """
    start_time = time.time()
    
    # 检查数据库连接（异步）
    db_status = "unknown"
    try:
        from app.core.database import db
        # 简单的ping测试
        await db.command('ping')
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # 检查Redis连接（异步）
    redis_status = "unknown"
    try:
        from app.core.database import redis_client
        await redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    elapsed_time = time.time() - start_time
    
    return {
        "success": True,
        "data": {
            "status": "ok",
            "version": get_version(),
            "timestamp": int(time.time()),
            "service": "TradingAgents-CN API",
            "checks": {
                "mongodb": db_status,
                "redis": redis_status
            },
            "response_time_ms": round(elapsed_time * 1000, 2)
        },
        "message": "服务运行正常"
    }

@router.get("/healthz")
async def healthz():
    """Kubernetes健康检查"""
    return {"status": "ok"}

@router.get("/readyz")
async def readyz():
    """Kubernetes就绪检查"""
    return {"ready": True}