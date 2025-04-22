import schedule
import time
import requests
import os
import logging
from dotenv import load_dotenv
from typing import Optional
from redis import Redis
from .redis_timeseries import RedisTimeSeriesManager

logger = logging.getLogger(__name__)

class BitcoinPriceService:
    def __init__(self, redis_client: Redis):
        load_dotenv()  # Load environment variables
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            logger.error("API_KEY not found in environment variables")
            raise ValueError("API_KEY not found in environment variables")
        self.ts_manager = RedisTimeSeriesManager(redis_client)
        self.setup_schedules()

    def setup_schedules(self):
        """Setup periodic tasks for data collection and aggregation"""
        # Collect price every minute
        schedule.every().minute.at(":00").do(self.collect_price)
        
        # Aggregate 5-min data
        schedule.every(5).minutes.at(":00").do(
            self.ts_manager.aggregate_price, "5min"
        )
        
        # Aggregate 15-min data
        schedule.every(15).minutes.at(":00").do(
            self.ts_manager.aggregate_price, "15min"
        )
        
        # Aggregate hourly data
        schedule.every().hour.at(":00").do(
            self.ts_manager.aggregate_price, "1h"
        )
        logger.info("Scheduled tasks setup completed")

    def collect_price(self) -> Optional[float]:
        """Collect current Bitcoin price from CoinMarketCap API and store it"""
        try:
            url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
            headers = {
                'Accepts': 'application/json',
                'X-CMC_PRO_API_KEY': self.api_key,
            }
            parameters = {
                'symbol': 'BTC',
                'convert': 'USD'
            }

            response = requests.get(url, headers=headers, params=parameters, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data['status']['error_code'] != 0:
                logger.error(f"API Error: {data['status']['error_message']}")
                return None

            price = data['data']['BTC']['quote']['USD']['price']
            if self.ts_manager.add_price(price):
                logger.info(f"Successfully stored BTC price: ${price:,.2f}")
                return price
            return None
        except Exception as e:
            logger.error(f"Error collecting price: {e}")
            return None

    def run(self):
        """Run the service indefinitely"""
        logger.info("Starting Bitcoin Price Service...")
        
        # Collect initial price
        self.collect_price()
        
        while True:
            schedule.run_pending()
            time.sleep(1)