from redis import Redis
from typing import Dict, Any
import json
import time
import signal
import sys
import os
import logging
from src.price_service import BitcoinPriceService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bitcoin_price_service.log')
    ]
)
logger = logging.getLogger(__name__)

def create_redis_connection() -> Redis:
    """Create a connection to Redis"""
    try:
        redis_client = Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD', 'mypassword'),
            decode_responses=True
        )
        redis_client.ping()  # Test the connection
        logger.info("Successfully connected to Redis")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)

def store_market_data(redis_client: Redis, symbol: str, data: Dict[str, Any]):
    """Store market data in Redis with timestamp"""
    try:
        # Add timestamp to the data
        data['timestamp'] = time.time()
        
        # Store data as a JSON string
        key = f"market:{symbol}"
        redis_client.set(key, json.dumps(data))
        logger.info(f"Stored data for {symbol}")
    except Exception as e:
        logger.error(f"Error storing data: {e}")

def get_market_data(redis_client: Redis, symbol: str) -> Dict[str, Any]:
    """Retrieve market data for a symbol"""
    try:
        key = f"market:{symbol}"
        data = redis_client.get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.error(f"Error retrieving data: {e}")
        return None

def clean_redis_data(redis_client: Redis):
    """Clean all Bitcoin price related data from Redis"""
    try:
        # Clean up all time series keys
        keys_to_delete = redis_client.keys("btc:price:*")
        if keys_to_delete:
            redis_client.delete(*keys_to_delete)
            logger.info("Successfully cleaned Redis time series data")
    except Exception as e:
        logger.error(f"Error cleaning Redis data: {e}")
        sys.exit(1)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutting down...")
    sys.exit(0)

def main():
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting Bitcoin Price Tracking Service")
    
    # Create Redis connection
    redis_client = create_redis_connection()
    
    # Clean existing Redis data
    clean_redis_data(redis_client)
    
    # Create and start the Bitcoin price service
    price_service = BitcoinPriceService(redis_client)
    
    try:
        logger.info("Service initialized, starting price tracking...")
        price_service.run()
    except Exception as e:
        logger.error(f"Error in price tracking service: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
