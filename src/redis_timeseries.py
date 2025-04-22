from redis import Redis
import time
import logging
from typing import List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class RedisTimeSeriesManager:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        # Initialize only if time series don't exist
        if not self._check_timeseries_exists():
            self._init_timeseries()

    def _check_timeseries_exists(self) -> bool:
        """Check if the time series already exist"""
        try:
            # Check if minute time series exists
            self.redis.execute_command('TS.INFO', 'btc:price:minute')
            return True
        except:
            return False

    def _init_timeseries(self):
        """Initialize Redis TimeSeries with retention periods"""
        try:
            # Minute-level price data (1 hour retention)
            self.redis.execute_command('TS.CREATE', 'btc:price:minute', 'RETENTION', 3600000, 'IF NOT EXISTS')
            
            # 5-minute aggregated data (1 hour retention)
            for suffix in ['', ':min', ':max']:
                self.redis.execute_command('TS.CREATE', f'btc:price:5min{suffix}', 'RETENTION', 3600000, 'IF NOT EXISTS')
            
            # 15-minute aggregated data (1 hour retention)
            for suffix in ['', ':min', ':max']:
                self.redis.execute_command('TS.CREATE', f'btc:price:15min{suffix}', 'RETENTION', 3600000, 'IF NOT EXISTS')
            
            # Hourly aggregated data (24 hour retention)
            for suffix in ['', ':min', ':max']:
                self.redis.execute_command('TS.CREATE', f'btc:price:hour{suffix}', 'RETENTION', 86400000, 'IF NOT EXISTS')
            
            logger.info("Successfully initialized Redis TimeSeries")
        except Exception as e:
            logger.error(f"Error initializing TimeSeries: {e}")
            raise

    def add_price(self, price: float, timestamp: Optional[int] = None) -> bool:
        """Add a new price point to the minute-level timeseries"""
        if timestamp is None:
            timestamp = int(time.time() * 1000)  # Redis TS expects milliseconds
        try:
            self.redis.execute_command('TS.ADD', 'btc:price:minute', timestamp, price)
            return True
        except Exception as e:
            logger.error(f"Error adding price: {e}")
            return False

    def get_last_n(self, key: str, n: int) -> List[Tuple[int, float]]:
        """Get the last n entries from a timeseries"""
        try:
            # Get the last n samples
            result = self.redis.execute_command('TS.RANGE', key, '-', '+', 'COUNT', n)
            return [(int(ts), float(val)) for ts, val in result]
        except Exception as e:
            logger.error(f"Error getting last {n} entries from {key}: {e}")
            return []

    def aggregate_price(self, resolution: str):
        """Aggregate price data for different time resolutions"""
        samples = {
            "5min": 5,
            "15min": 15,
            "1h": 60
        }
        
        n = samples.get(resolution)
        if not n:
            logger.error(f"Invalid resolution: {resolution}")
            raise ValueError(f"Invalid resolution: {resolution}")

        # Get the last n minute-level prices
        entries = self.get_last_n('btc:price:minute', n)
        if not entries:
            logger.warning(f"No data available for {resolution} aggregation")
            return False

        # Extract just the prices
        prices = [price for _, price in entries]
        timestamp = entries[-1][0]  # Use the timestamp of the latest entry

        # Calculate aggregates
        min_price = min(prices)
        max_price = max(prices)
        last_price = prices[-1]

        try:
            base_key = f'btc:price:{resolution}'
            self.redis.execute_command('TS.ADD', base_key, timestamp, last_price)
            self.redis.execute_command('TS.ADD', f'{base_key}:min', timestamp, min_price)
            self.redis.execute_command('TS.ADD', f'{base_key}:max', timestamp, max_price)
            logger.info(f"Successfully aggregated {resolution} data")
            return True
        except Exception as e:
            logger.error(f"Error storing aggregated data for {resolution}: {e}")
            return False