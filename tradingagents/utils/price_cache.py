# -*- coding: utf-8 -*-
"""
Unified Price Cache Module
Ensures all analysts use the same price cache mechanism
Supports multi-level cache strategy (Memory + Redis)
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json

logger = logging.getLogger(__name__)


class UnifiedPriceCache:
    """Unified Price Cache Class (Singleton)

    Multi-level cache strategy:
    - L1: Memory cache (fast, process-shared)
    - L2: Redis cache (distributed, multi-process shared)
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(UnifiedPriceCache, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Cache structure: {ticker: {'price': float, 'currency': str, 'timestamp': datetime, 'data': dict}}
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.memory_ttl_seconds = 600  # Memory cache TTL: 10 minutes
        self.redis_ttl_seconds = 1800  # Redis cache TTL: 30 minutes
        self.cache_lock = threading.Lock()

        # Redis client initialization
        self._redis_client = None
        self._redis_available = False
        self._init_redis()

        logger.info("[UnifiedPriceCache] Price cache initialized")

    def _init_redis(self):
        """Initialize Redis client"""
        try:
            import redis
            import os

            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            redis_db = int(os.getenv("REDIS_DB", 0))

            self._redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._redis_client.ping()
            self._redis_available = True
            logger.info(
                f"[UnifiedPriceCache] Redis cache connected: {redis_host}:{redis_port}"
            )
        except Exception as e:
            logger.warning(
                f"[UnifiedPriceCache] Redis not available, using memory-only mode: {e}"
            )
            self._redis_available = False

    def _check_redis_connection(self) -> bool:
        """Check Redis connection and attempt to reconnect if needed"""
        if self._redis_client is None:
            return False
        try:
            self._redis_client.ping()
            return True
        except Exception:
            return False

    def _ensure_redis_connected(self):
        """Ensure Redis is connected, attempt reconnection if needed"""
        if not self._redis_available and self._check_redis_connection():
            logger.info("[UnifiedPriceCache] Redis reconnected successfully")
            self._redis_available = True
        elif not self._redis_available:
            # Attempt reconnection once
            try:
                import redis
                import os

                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", 6379))
                redis_db = int(os.getenv("REDIS_DB", 0))
                self._redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                self._redis_client.ping()
                self._redis_available = True
                logger.info(
                    f"[UnifiedPriceCache] Redis reconnected: {redis_host}:{redis_port}"
                )
            except Exception as e:
                self._redis_available = False
                logger.debug(f"[UnifiedPriceCache] Redis reconnection failed: {e}")

    def _get_redis_key(self, ticker: str) -> str:
        """Generate Redis key"""
        return f"price_cache:{ticker}"

    def _is_valid(self, entry: Dict[str, Any]) -> bool:
        """Check if entry is valid"""
        if not entry or "timestamp" not in entry:
            return False

        try:
            ts = entry["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            elif not isinstance(ts, datetime):
                return False
            age = (datetime.now() - ts).total_seconds()
            return age < self.memory_ttl_seconds
        except (ValueError, TypeError, OSError):
            return False

    def get_price(self, ticker: str) -> Optional[float]:
        """Get cached price (prefer Redis, then memory)"""
        # Ensure Redis is connected before attempting read
        if self._redis_available:
            self._ensure_redis_connected()
            if not self._redis_available:
                logger.debug("[PriceCache] Redis unavailable, using memory cache only")

        if self._redis_available:
            try:
                redis_key = self._get_redis_key(ticker)
                redis_data = self._redis_client.get(redis_key)
                if redis_data:
                    data = json.loads(redis_data)
                    price = data.get("price")
                    if price is not None:
                        logger.debug(f"[PriceCache] Redis hit: {ticker} = {price}")
                        return float(price)
            except Exception as e:
                logger.warning(f"[PriceCache] Redis read failed: {e}")
                # Try to reconnect on next attempt
                self._redis_available = False

        with self.cache_lock:
            if ticker in self.cache:
                entry = self.cache[ticker]
                if self._is_valid(entry):
                    logger.debug(
                        f"[PriceCache] Memory hit: {ticker} = {entry['price']}"
                    )
                    return entry["price"]
        return None

    def get_historical_prices(
        self, ticker: str, start_date: str, end_date: str
    ) -> Optional[List[Dict]]:
        """Get cached historical price data"""
        # Normalize date format to ensure cache key consistency
        normalized_start = self._normalize_date(start_date)
        normalized_end = self._normalize_date(end_date)

        if self._redis_available:
            self._ensure_redis_connected()
            if not self._redis_available:
                logger.debug(
                    "[PriceCache] Redis unavailable, skipping historical price cache"
                )

        if self._redis_available:
            try:
                redis_key = (
                    f"price_history:{ticker}:{normalized_start}:{normalized_end}"
                )
                redis_data = self._redis_client.get(redis_key)
                if redis_data:
                    data = json.loads(redis_data)
                    logger.debug(f"[PriceCache] Historical price Redis hit: {ticker}")
                    return data
            except Exception as e:
                logger.warning(f"[PriceCache] Redis historical price read failed: {e}")
                self._redis_available = False
        return None

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """Normalize date string to YYYY-MM-DD format"""
        try:
            from datetime import datetime

            # Try parsing various date formats
            formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            # If no format matches, return original
            return date_str
        except Exception:
            return date_str

    def get_price_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get complete price info (prefer Redis, then memory)"""
        if self._redis_available:
            try:
                redis_key = self._get_redis_key(ticker)
                redis_data = self._redis_client.get(redis_key)
                if redis_data:
                    data = json.loads(redis_data)
                    timestamp = datetime.fromisoformat(
                        data.get("timestamp", "2000-01-01")
                    )
                    age = (datetime.now() - timestamp).total_seconds()
                    if age < self.redis_ttl_seconds:
                        logger.debug(f"[PriceCache] Price info Redis hit: {ticker}")
                        return data
            except Exception as e:
                logger.warning(f"[PriceCache] Redis price info read failed: {e}")

        with self.cache_lock:
            if ticker in self.cache:
                entry = self.cache[ticker]
                if self._is_valid(entry):
                    logger.debug(f"[PriceCache] Price info memory hit: {ticker}")
                    return entry.copy()
        return None

    def update(
        self,
        ticker: str,
        price: float,
        currency: str = "CNY",
        data: Dict[str, Any] = None,
    ):
        """
        Update cache (both Redis and memory)

        Args:
            ticker: Stock ticker
            price: Price value
            currency: Currency symbol
            data: Additional data dict
        """
        entry = {
            "price": float(price),
            "currency": currency,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        }

        # Update memory cache (with 10s debounce)
        with self.cache_lock:
            if ticker in self.cache:
                old_entry = self.cache[ticker]
                age = (
                    datetime.now() - datetime.fromisoformat(old_entry["timestamp"])
                ).total_seconds()
                if age < 10:  # Skip if updated within 10 seconds
                    return

            self.cache[ticker] = entry
            expire_time = (
                datetime.now() + timedelta(seconds=self.memory_ttl_seconds)
            ).strftime("%H:%M:%S")
            logger.info(
                f"[PriceCache] {ticker} updated: {currency}{price:.2f}, memory expire: {expire_time}"
            )

        # Update Redis cache
        if self._redis_available:
            try:
                redis_key = self._get_redis_key(ticker)
                self._redis_client.setex(
                    redis_key,
                    self.redis_ttl_seconds,
                    json.dumps(entry, ensure_ascii=False),
                )
                redis_expire = (
                    datetime.now() + timedelta(seconds=self.redis_ttl_seconds)
                ).strftime("%H:%M:%S")
                logger.debug(
                    f"[PriceCache] Redis updated: {ticker}, expire: {redis_expire}"
                )
            except Exception as e:
                logger.warning(f"[PriceCache] Redis update failed: {e}")

    def cache_price_data(self, ticker: str, price_data: dict):
        """Cache complete price data"""
        if not price_data:
            return

        price = price_data.get("price", 0)
        currency = price_data.get("currency", "CNY")

        with self.cache_lock:
            self.cache[ticker] = {
                "price": float(price),
                "currency": currency,
                "timestamp": datetime.now(),
                "data": price_data,
            }

        if self._redis_available:
            try:
                redis_key = self._get_redis_key(ticker)
                entry = {
                    "price": float(price),
                    "currency": currency,
                    "timestamp": datetime.now().isoformat(),
                    "data": price_data,
                }
                self._redis_client.setex(
                    redis_key,
                    self.redis_ttl_seconds,
                    json.dumps(entry, ensure_ascii=False),
                )
            except Exception as e:
                logger.warning(f"[PriceCache] Redis cache_price_data failed: {e}")

    def cache_historical_prices(
        self, ticker: str, start_date: str, end_date: str, prices: list
    ):
        """Cache historical price data to Redis"""
        if not self._redis_available or not prices:
            return

        try:
            redis_key = f"price_history:{ticker}:{start_date}:{end_date}"
            self._redis_client.setex(
                redis_key,
                self.redis_ttl_seconds,
                json.dumps(prices, ensure_ascii=False, default=str),
            )
            logger.debug(
                f"[PriceCache] Historical prices cached to Redis: {ticker} ({len(prices)} records)"
            )
        except Exception as e:
            logger.warning(f"[PriceCache] Historical price cache failed: {e}")

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get cached current price"""
        return self.get_price(ticker)

    def is_price_fresh(self, ticker: str, max_age_seconds: int = 600) -> bool:
        """Check if price data is fresh"""
        if self._redis_available:
            try:
                redis_key = self._get_redis_key(ticker)
                ttl = self._redis_client.ttl(redis_key)
                if ttl > 0:
                    return True
            except Exception:
                pass

        with self.cache_lock:
            if ticker in self.cache:
                entry = self.cache[ticker]
                if self._is_valid(entry):
                    age = (datetime.now() - entry["timestamp"]).total_seconds()
                    return age < max_age_seconds
        return False

    def get_cached_tickers(self) -> List[str]:
        """Get all cached tickers"""
        with self.cache_lock:
            valid_tickers = []
            for ticker, entry in self.cache.items():
                if self._is_valid(entry):
                    valid_tickers.append(ticker)
            return valid_tickers

    def clear(self, ticker: str = None):
        """Clear cache"""
        with self.cache_lock:
            if ticker:
                if ticker in self.cache:
                    del self.cache[ticker]
                    logger.debug(f"[PriceCache] {ticker} cleared")

                if self._redis_available:
                    try:
                        redis_key = self._get_redis_key(ticker)
                        self._redis_client.delete(redis_key)
                    except Exception as e:
                        logger.warning(f"[PriceCache] Redis clear failed: {e}")
            else:
                self.cache.clear()
                logger.debug("[PriceCache] All cleared")

                if self._redis_available:
                    try:
                        pattern = "price_cache:*"
                        keys = self._redis_client.keys(pattern)
                        if keys:
                            self._redis_client.delete(*keys)
                        pattern = "price_history:*"
                        keys = self._redis_client.keys(pattern)
                        if keys:
                            self._redis_client.delete(*keys)
                    except Exception as e:
                        logger.warning(f"[PriceCache] Redis clear all failed: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.cache_lock:
            valid_count = 0
            for entry in self.cache.values():
                try:
                    ts = entry.get("timestamp")
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts)
                    elif not isinstance(ts, datetime):
                        continue
                    age = (datetime.now() - ts).total_seconds()
                    if age < self.memory_ttl_seconds:
                        valid_count += 1
                except (ValueError, TypeError, OSError):
                    continue
            return {
                "memory_cache_count": len(self.cache),
                "valid_memory_cache": valid_count,
                "redis_available": self._redis_available,
                "memory_ttl_seconds": self.memory_ttl_seconds,
                "redis_ttl_seconds": self.redis_ttl_seconds,
            }


# Global singleton getter
def get_price_cache() -> UnifiedPriceCache:
    return UnifiedPriceCache()
