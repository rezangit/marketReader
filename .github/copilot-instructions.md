<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

Project Description: 

this project is to have a short history of bitcoin market data to use for market short pridiction using RSA algorithm

it contained 2 part

first part is to call API and read minute cost data
second part is to store this information in database and generate history by it

first part:
call coinmarketcap.com API and get the last price

second part:
Design a real-time data storage solution for Bitcoin price tracking using Redis TimeSeries, optimized for low-latency access and rolling data retention. The system supports multiple time resolutions and captures both price points and volatility metrics (min/max) for enhanced market signal processing.

✅ Data Design & Storage Plan
We will use Redis TimeSeries to store Bitcoin price data across four resolutions:

1. Minute-Level Price Data
Key Name: btc:price:minute

Frequency: 1 entry per minute

Fields:

price: latest BTC price

Retention: 60 entries (1 hour)

Purpose: Core data feed used to generate 5-minute and 15-minute aggregates.

bash
Copy
Edit
TS.CREATE btc:price:minute RETENTION 3600000
2. 5-Minute Aggregated Price Data
Key Name: btc:price:5min

Frequency: 1 entry every 5 minutes

Fields:

price: closing price at the 5-minute mark

min: lowest price in the last 5 minutes

max: highest price in the last 5 minutes

Retention: 12 entries (1 hour)

How it's updated:
A background function reads the last 5 entries from btc:price:minute every 5 minutes and calculates:

python
Copy
Edit
min = min(prices[-5:])
max = max(prices[-5:])
price = prices[-1]  # latest price
bash
Copy
Edit
TS.CREATE btc:price:5min RETENTION 3600000
3. 15-Minute Aggregated Price Data
Key Name: btc:price:15min

Frequency: 1 entry every 15 minutes

Fields:

price: closing price at 15-minute mark

min: lowest price in 15 minutes

max: highest price in 15 minutes

Retention: 4 entries (1 hour)

Update Method: Similar logic as 5-minute aggregation but across last 15 entries of btc:price:minute.

bash
Copy
Edit
TS.CREATE btc:price:15min RETENTION 3600000
4. Hourly Aggregated Price Data
Key Name: btc:price:hour

Frequency: 1 entry every hour

Fields:

price: closing price at the hour

min: lowest price in 60 minutes

max: highest price in 60 minutes

Retention: 24 entries (1 day)

Updated From: btc:price:minute (last 60 entries) or btc:price:5min if preferred.

bash
Copy
Edit
TS.CREATE btc:price:hour RETENTION 86400000

Aggregation Function Logic (Pseudocode)
python
Copy
Edit
def aggregate_price(resolution):
    if resolution == "5min":
        prices = get_last_n("btc:price:minute", 5)
    elif resolution == "15min":
        prices = get_last_n("btc:price:minute", 15)
    elif resolution == "1h":
        prices = get_last_n("btc:price:minute", 60)

    min_price = min(prices)
    max_price = max(prices)
    last_price = prices[-1]

    redis_ts_add(f"btc:price:{resolution}", timestamp=now(), value=last_price)
    redis_ts_add(f"btc:price:{resolution}:min", timestamp=now(), value=min_price)
    redis_ts_add(f"btc:price:{resolution}:max", timestamp=now(), value=max_price)
Alternatively, you can store all three values in one key using labels/tags or multi-key pattern depending on your architecture.
