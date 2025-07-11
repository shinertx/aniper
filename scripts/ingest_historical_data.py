#!/usr/bin/env python3
from __future__ import annotations

import datetime
import random
import uuid
from pathlib import Path

import pandas as pd
from faker import Faker

# Ensure the output directory exists
output_dir = Path("tests/data")
output_dir.mkdir(exist_ok=True)
OUTPUT_PATH = output_dir / "historical_data.parquet"
NUM_MONTHS = 6
RECORDS_PER_DAY = 500  # Average number of new tokens per day per platform


def generate_historical_data(platform: str, faker: Faker, end_date: datetime.datetime, days: int) -> pd.DataFrame:
    """Generates realistic historical memecoin data for a single platform."""
    data = []
    for day in range(days):
        current_date = end_date - datetime.timedelta(days=day)
        for _ in range(RECORDS_PER_DAY):
            timestamp = current_date - datetime.timedelta(seconds=random.randint(0, 86399))
            
            # Simulate market dynamics
            market_cap = random.uniform(1000, 5_000_000) * (1 + 0.1 * (days - day) / days) # Older coins tend to be larger
            is_rugpull = random.random() < (0.6 if market_cap < 20000 else 0.2) # High failure rate for low-cap
            trade_volume = market_cap * random.uniform(0.1, 3.0) if not is_rugpull else market_cap * random.uniform(0.01, 0.2)

            data.append({
                "timestamp": timestamp,
                "platform": platform,
                "token_address": f"tok_{uuid.uuid4().hex[:16]}",
                "creator_address": f"creator_{uuid.uuid4().hex[:16]}",
                "name": faker.company() + " Coin",
                "symbol": faker.currency_code() + str(random.randint(1, 99)),
                "description": faker.catch_phrase(),
                "market_cap_usd": round(market_cap, 2),
                "trade_volume_24h": round(trade_volume, 2),
                "is_rugpull": is_rugpull,
                "raw_event_data": f"event_{uuid.uuid4().hex}",
            })
    return pd.DataFrame(data)


def main():
    """Main function to generate and save the historical dataset."""
    print("Starting historical data generation...")
    faker = Faker()
    end_date = datetime.datetime.now(datetime.timezone.utc)
    total_days = NUM_MONTHS * 30

    print(f"Generating data for 'pump.fun' for {total_days} days...")
    pump_fun_data = generate_historical_data("pump.fun", faker, end_date, total_days)

    print(f"Generating data for 'letsbonk.dev' for {total_days} days...")
    letsbonk_data = generate_historical_data("letsbonk.dev", faker, end_date, total_days)

    print("Combining datasets...")
    combined_data = pd.concat([pump_fun_data, letsbonk_data], ignore_index=True)
    
    # Sort by timestamp to simulate a real-time feed
    combined_data = combined_data.sort_values(by="timestamp", ascending=True).reset_index(drop=True)

    print(f"Saving {len(combined_data)} records to {OUTPUT_PATH}...")
    combined_data.to_parquet(OUTPUT_PATH, engine="fastparquet", compression="gzip")
    
    print("✅ Historical data generation complete.")
    print(f"Total records: {len(combined_data)}")
    print(f"File saved to: {OUTPUT_PATH}")
    print("\nSample of generated data:")
    print(combined_data.head())


if __name__ == "__main__":
    main()
