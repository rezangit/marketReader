import unittest
import time
from redis import Redis
from src.redis_timeseries import RedisTimeSeriesManager

class TestRedisTimeSeriesManager(unittest.TestCase):
    def setUp(self):
        self.redis = Redis(
            host='localhost',
            port=6379,
            password='mypassword',
            decode_responses=True
        )
        # Clean up any existing keys before each test
        self.redis.flushdb()
        self.ts_manager = RedisTimeSeriesManager(self.redis)
        
    def test_add_price(self):
        """Test adding a price point"""
        price = 45000.0
        result = self.ts_manager.add_price(price)
        self.assertTrue(result)
        
        # Verify the price was stored
        entries = self.ts_manager.get_last_n('btc:price:minute', 1)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][1], price)
        
    def test_aggregate_5min(self):
        """Test 5-minute aggregation"""
        # Add test prices
        prices = [45000.0, 45100.0, 45200.0, 45150.0, 45300.0]
        for price in prices:
            self.ts_manager.add_price(price)
            time.sleep(0.1)  # Small delay between entries
            
        # Trigger 5-minute aggregation
        self.ts_manager.aggregate_price("5min")
        
        # Verify aggregated data
        base_key = 'btc:price:5min'
        entries = self.ts_manager.get_last_n(base_key, 1)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][1], prices[-1])  # Last price
        
        min_entries = self.ts_manager.get_last_n(f'{base_key}:min', 1)
        self.assertEqual(min_entries[0][1], min(prices))
        
        max_entries = self.ts_manager.get_last_n(f'{base_key}:max', 1)
        self.assertEqual(max_entries[0][1], max(prices))

    def tearDown(self):
        """Clean up after each test"""
        self.redis.flushdb()

if __name__ == '__main__':
    unittest.main()