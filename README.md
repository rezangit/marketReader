# Bitcoin Price Data Tracker with Redis TimeSeries

A real-time data storage solution for Bitcoin price tracking using Redis TimeSeries, optimized for low-latency access and rolling data retention. The system supports multiple time resolutions and captures both price points and volatility metrics.

## Features
- Real-time price data storage at multiple resolutions (1min, 5min, 15min, 1hour)
- Automated data aggregation and retention policies
- Min/max price tracking for volatility analysis
- Efficient data storage with automatic cleanup

## Data Design
### 1. Minute-Level Price Data (btc:price:minute)
- Frequency: 1 entry per minute
- Retention: 60 entries (1 hour)
- Fields: price (latest BTC price)

### 2. 5-Minute Aggregated Data (btc:price:5min)
- Frequency: 1 entry every 5 minutes
- Retention: 12 entries (1 hour)
- Fields: price (closing), min, max

### 3. 15-Minute Aggregated Data (btc:price:15min)
- Frequency: 1 entry every 15 minutes
- Retention: 4 entries (1 hour)
- Fields: price (closing), min, max

### 4. Hourly Aggregated Data (btc:price:hour)
- Frequency: 1 entry every hour
- Retention: 24 entries (1 day)
- Fields: price (closing), min, max

## Project Structure
- `main.py`: Entry point for the application
- `src/`: Source code
  - `price_service.py`: Price data collection service
  - `redis_timeseries.py`: Redis TimeSeries implementation
- `tests/`: Test code
- `requirements.txt`: Project dependencies
- `docker-compose.yml`: Docker configuration for Redis
- `redis.conf`: Redis configuration

## Requirements
- Python 3.x
- Redis with RedisTimeSeries module
- Docker (for running Redis)

## Deployment with Docker Compose

### Prerequisites
- Docker and Docker Compose installed on your system
- A CoinMarketCap API key (set in .env file)

### Environment Setup
1. Create a `.env` file in the project root with the following content:
```
API_KEY=your_coinmarketcap_api_key
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=mypassword
```

### Docker Commands

Build and start the services:
```bash
docker compose up --build -d
```

View the logs:
```bash
docker compose logs -f
```

Stop the services:
```bash
docker compose down
```

Restart services:
```bash
docker compose restart
```

Rebuild a specific service (after code changes):
```bash
docker compose up -d --build price_tracker
```

### Accessing the Services
- Redis is accessible at `localhost:6379`
- Redis password is set in the .env file
- The price tracker service will automatically start collecting data

### Monitoring
To view the stored data, you can use:
1. Redis CLI: `docker compose exec redis redis-cli -a mypassword`
2. The included table viewer: `python table_viewer.py`

### Troubleshooting
- If the services fail to start, check the logs using `docker compose logs`
- Ensure all required environment variables are set in the .env file
- Verify your CoinMarketCap API key is valid
