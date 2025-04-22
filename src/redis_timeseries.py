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
        """Initialize Redis TimeSeries with retention periods and uncompressed storage"""
        try:
            # Constants for retention calculation
            MS_PER_MINUTE = 60 * 1000
            MS_PER_HOUR = 60 * MS_PER_MINUTE

            # Minute-level price data (120 samples = 2 hours)
            self.redis.execute_command('TS.CREATE', 'btc:price:minute', 
                                     'RETENTION', 2 * MS_PER_HOUR,
                                     'UNCOMPRESSED',
                                     'DUPLICATE_POLICY', 'LAST',
                                     'IF NOT EXISTS')
            
            # 5-minute aggregated data (24 samples = 2 hours)
            for suffix in ['', ':min', ':max']:
                self.redis.execute_command('TS.CREATE', f'btc:price:5min{suffix}', 
                                         'RETENTION', 2 * MS_PER_HOUR,
                                         'UNCOMPRESSED',
                                         'DUPLICATE_POLICY', 'LAST',
                                         'IF NOT EXISTS')
            
            # 15-minute aggregated data (8 samples = 2 hours)
            for suffix in ['', ':min', ':max']:
                self.redis.execute_command('TS.CREATE', f'btc:price:15min{suffix}', 
                                         'RETENTION', 2 * MS_PER_HOUR,
                                         'UNCOMPRESSED',
                                         'DUPLICATE_POLICY', 'LAST',
                                         'IF NOT EXISTS')
            
            # Hourly aggregated data (24 samples = 24 hours)
            for suffix in ['', ':min', ':max']:
                self.redis.execute_command('TS.CREATE', f'btc:price:hour{suffix}', 
                                         'RETENTION', 24 * MS_PER_HOUR,
                                         'UNCOMPRESSED',
                                         'DUPLICATE_POLICY', 'LAST',
                                         'IF NOT EXISTS')
            
            logger.info("Successfully initialized Redis TimeSeries with circular buffer configuration")
        except Exception as e:
            logger.error(f"Error initializing TimeSeries: {e}")
            raise

    def _align_timestamp(self, timestamp: int, resolution: str) -> int:
        """Align timestamp to resolution boundaries"""
        ms_in_minute = 60 * 1000
        align_to = {
            'minute': ms_in_minute,
            '5min': 5 * ms_in_minute,
            '15min': 15 * ms_in_minute,
            'hour': 60 * ms_in_minute
        }
        interval = align_to.get(resolution, ms_in_minute)
        return (timestamp // interval) * interval

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

    def aggregate_price(self, resolution: str, entries=None):
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

        # Use provided entries or get the last n entries
        if entries is None:
            entries = self.get_last_n('btc:price:minute', n)
        
        if len(entries) < n:
            logger.warning(f"Insufficient data for {resolution} aggregation. Need {n} entries, got {len(entries)}")
            return False

        # Extract prices and ensure they're in chronological order
        entries = sorted(entries, key=lambda x: x[0])
        prices = [price for _, price in entries]
        
        # Align timestamp to resolution boundary
        timestamp = self._align_timestamp(entries[-1][0], resolution)

        try:
            base_key = f'btc:price:{resolution}'
            # Simply add the new aggregated values - Redis handles retention automatically
            self.redis.execute_command('TS.ADD', base_key, timestamp, prices[-1])  # Closing price
            self.redis.execute_command('TS.ADD', f'{base_key}:min', timestamp, min(prices))
            self.redis.execute_command('TS.ADD', f'{base_key}:max', timestamp, max(prices))
            
            logger.info(f"Added {resolution} data: close=${prices[-1]:,.2f}, "
                       f"min=${min(prices):,.2f}, max=${max(prices):,.2f}")
            return True
        except Exception as e:
            logger.error(f"Error storing aggregated data for {resolution}: {e}")
            return False