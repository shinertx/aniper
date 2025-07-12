import pandas as pd
import requests
import os

# --- Configuration ---
DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "YOUR_DUNE_API_KEY")
DUNE_QUERY_ID = "123456" # Replace with the actual query ID for "pump-fun-launches-2024"
OUTPUT_DIR = "tests/data"
OUTPUT_FILE = f"{OUTPUT_DIR}/historical_data.parquet"

def fetch_dune_data(query_id, api_key):
    """Fetches data from a Dune Analytics query."""
    url = f"https://api.dune.com/api/v1/query/{query_id}/results?api_key={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Dune Analytics: {e}")
        return None

def main():
    """Main function to ingest and process historical data."""
    print("Starting historical data ingestion...")

    # --- Fetch Pump.fun Data ---
    print("Fetching pump.fun data from Dune Analytics...")
    dune_data = fetch_dune_data(DUNE_QUERY_ID, DUNE_API_KEY)
    if dune_data and 'result' in dune_data and 'rows' in dune_data['result']:
        pump_fun_df = pd.DataFrame(dune_data['result']['rows'])
        print(f"Successfully fetched {len(pump_fun_df)} rows from Dune Analytics.")

        # --- Ensure output directory exists ---
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        # --- Save to Parquet ---
        pump_fun_df.to_parquet(OUTPUT_FILE)
        print(f"Successfully saved data to {OUTPUT_FILE}")
    else:
        print("Failed to fetch or process data from Dune Analytics.")

if __name__ == "__main__":
    main()
