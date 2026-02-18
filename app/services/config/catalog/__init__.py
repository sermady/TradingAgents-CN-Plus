# -*- coding: utf-8 -*-
"""
模型目录模块

提供模型目录管理和默认模型数据
"""

from .data import get_default_model_catalog
from .service import ModelCatalogService

__all__ = ["ModelCatalogService", "get_default_model_catalog"]
