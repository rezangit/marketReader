#!/usr/bin/env python3
from redis import Redis
from src.redis_timeseries import RedisTimeSeriesManager
from datetime import datetime, timedelta
import argparse
import sys
from typing import List, Tuple

class TimeSeriesViewer:
    def __init__(self):
        self.redis_client = self._create_redis_connection()
        self.ts_manager = self._create_ts_manager()

    def _create_redis_connection(self) -> Redis:
        """Create a connection to Redis"""
        try:
            redis_client = Redis(
                host='localhost',
                port=6379,
                password='mypassword',
                decode_responses=True
            )
            redis_client.ping()
            return redis_client
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            sys.exit(1)

    def _create_ts_manager(self):
        """Create TimeSeries manager without initialization"""
        class ViewOnlyManager(RedisTimeSeriesManager):
            def _init_timeseries(self):
                # Skip initialization since keys are managed by the main service
                pass
        
        return ViewOnlyManager(self.redis_client)

    def format_price_data(self, entries: List[Tuple[int, float]], show_header: bool = True) -> str:
        """Format price data as a table"""
        if not entries:
            return "No data available"
        
        output = []
        if show_header:
            output.append("Timestamp                 | Price (USD)")
            output.append("-" * 40)
        
        for timestamp_ms, price in entries:
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            output.append(f"{formatted_time} | ${price:,.2f}")
        
        return "\n".join(output)

    def display_resolution_data(self, resolution: str, count: int = None):
        """Display data for a specific time resolution"""
        base_key = f'btc:price:{resolution}'
        
        # Get count based on resolution if not specified
        if count is None:
            count = {
                'minute': 60,
                '5min': 12,
                '15min': 4,
                'hour': 24
            }.get(resolution, 10)

        print(f"\n{resolution.upper()} Resolution Data:")
        print("-" * 50)
        
        # Get main price data
        entries = self.ts_manager.get_last_n(base_key, count)
        print(self.format_price_data(entries))
        
        # Get min/max data for aggregated resolutions
        if resolution != 'minute':
            min_entries = self.ts_manager.get_last_n(f'{base_key}:min', 1)
            max_entries = self.ts_manager.get_last_n(f'{base_key}:max', 1)
            
            if min_entries and max_entries:
                print(f"\nLast Period Statistics:")
                print(f"Min Price: ${min_entries[0][1]:,.2f}")
                print(f"Max Price: ${max_entries[0][1]:,.2f}")
                if entries:
                    print(f"Close Price: ${entries[-1][1]:,.2f}")
                    price_range = max_entries[0][1] - min_entries[0][1]
                    price_range_pct = (price_range / min_entries[0][1]) * 100
                    print(f"Price Range: ${price_range:,.2f} ({price_range_pct:.2f}%)")

def main():
    parser = argparse.ArgumentParser(description='View Bitcoin price time series data')
    parser.add_argument('--resolution', '-r', choices=['minute', '5min', '15min', 'hour'],
                      default='minute', help='Time resolution to display')
    parser.add_argument('--count', '-n', type=int, help='Number of entries to display')
    parser.add_argument('--all', '-a', action='store_true', 
                      help='Display data for all resolutions')
    
    args = parser.parse_args()
    viewer = TimeSeriesViewer()
    
    if args.all:
        for resolution in ['minute', '5min', '15min', 'hour']:
            viewer.display_resolution_data(resolution)
    else:
        viewer.display_resolution_data(args.resolution, args.count)

if __name__ == '__main__':
    main()