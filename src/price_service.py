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
        
        # Initialize counters
        self.minute_counter = 1
        self.five_min_counter = 1
        self.fifteen_min_counter = 1
        
        self.setup_schedules()

    def setup_schedules(self):
        """Setup periodic tasks for data collection"""
        # Collect price every minute
        schedule.every().minute.at(":00").do(self.collect_price)
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
                # Process aggregations based on counters
                self._process_aggregations()
                return price
            return None
        except Exception as e:
            logger.error(f"Error collecting price: {e}")
            return None

    def _process_aggregations(self):
        """Process aggregations using counter-based approach"""
        logger.info(f"Minute counter: {self.minute_counter}, 5-min counter: {self.five_min_counter}, 15-min counter: {self.fifteen_min_counter}")
        
        # Increment minute counter
        self.minute_counter += 1
        
        # Check if we have 5 minutes worth of data
        if self.minute_counter > 5:
            entries = self.ts_manager.get_last_n('btc:price:minute', 5)
            if len(entries) == 5:
                logger.info("Creating 5-minute aggregation")
                self.ts_manager.aggregate_price("5min", entries)
            
            # Reset minute counter and increment 5-min counter
            self.minute_counter = 1
            self.five_min_counter += 1
            
            # Check if we have 3 5-minute periods (15 minutes worth of data)
            if self.five_min_counter > 3:
                entries = self.ts_manager.get_last_n('btc:price:minute', 15)
                if len(entries) == 15:
                    logger.info("Creating 15-minute aggregation")
                    self.ts_manager.aggregate_price("15min", entries)
                
                # Reset 5-min counter and increment 15-min counter
                self.five_min_counter = 1
                self.fifteen_min_counter += 1
                
                # Check if we have 4 15-minute periods (1 hour worth of data)
                if self.fifteen_min_counter > 4:
                    entries = self.ts_manager.get_last_n('btc:price:minute', 60)
                    if len(entries) == 60:
                        logger.info("Creating hourly aggregation")
                        self.ts_manager.aggregate_price("1h", entries)
                    
                    # Reset 15-min counter
                    self.fifteen_min_counter = 1

    def run(self):
        """Run the service indefinitely"""
        logger.info("Starting Bitcoin Price Service...")
        
        # Collect initial price
        self.collect_price()
        
        while True:
            schedule.run_pending()
            time.sleep(1)