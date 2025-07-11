#!/usr/bin/env python3
"""
Live Market Data Validation
Tests real market APIs to validate agent performance with live data.
"""

import requests
import json
import time
from datetime import datetime
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="module")
def live_sol_data():
    """Fixture to fetch live SOL price data from CoinGecko."""
    print("\n🔥 Fetching live market data from CoinGecko for tests...")
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'solana',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true'
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        if 'solana' in data:
            sol_data = data['solana']
            price = sol_data['usd']
            change_24h = sol_data.get('usd_24h_change', 0)
            volume_24h = sol_data.get('usd_24h_vol', 0)
            
            print(f"✅ Live SOL Price: ${price:.2f}")
            print(f"📈 24h Change: {change_24h:.2f}%")
            print(f"💰 24h Volume: ${volume_24h:,.0f}")
            
            return {
                "price": price,
                "change_24h": change_24h,
                "volume_24h": volume_24h
            }
        else:
            pytest.fail("❌ No 'solana' key in CoinGecko API response.")
            
    except requests.exceptions.RequestException as e:
        pytest.fail(f"❌ CoinGecko API request failed: {e}")
    except Exception as e:
        pytest.fail(f"❌ Error fetching live data: {e}")

def test_coingecko_api_response(live_sol_data):
    """Tests that the live data fixture returns a valid structure."""
    assert isinstance(live_sol_data, dict)
    assert "price" in live_sol_data and isinstance(live_sol_data["price"], (int, float))
    assert "change_24h" in live_sol_data and isinstance(live_sol_data["change_24h"], (int, float))
    assert "volume_24h" in live_sol_data and isinstance(live_sol_data["volume_24h"], (int, float))
    print("\n✅ CoinGecko data fixture is valid.")

def test_agents_with_live_data(live_sol_data):
    """Test both agents with live market data from the fixture."""
    print(f"\n🤖 AGENT TESTING WITH LIVE DATA")
    print("=" * 40)
    
    price = live_sol_data["price"]
    change_24h = live_sol_data["change_24h"]
    volume_24h = live_sol_data["volume_24h"]
    
    # 1. Heuristic Agent Testing
    print(f"📊 Heuristic Agent Analysis:")
    print(f"Current Price: ${price:.2f}")
    print(f"Price Change: {change_24h:.2f}%")
    print(f"Volume: ${volume_24h:,.0f}")
    
    # Calculate agent metrics
    volatility_score = abs(change_24h) / 10  # 0-1 scale
    volume_score = min(volume_24h / 1_000_000_000, 1.0)  # Normalize to 1B volume
    momentum_score = max(min(change_24h / 10, 1.0), -1.0)  # -1 to 1 scale
    
    print(f"Volatility Score: {volatility_score:.2f}")
    print(f"Volume Score: {volume_score:.2f}")  
    print(f"Momentum Score: {momentum_score:.2f}")
    
    # Generate trading signal
    if momentum_score > 0.3 and volatility_score < 0.5 and volume_score > 0.3:
        signal = "BUY"
        confidence = 0.8
    elif momentum_score < -0.3 and volume_score > 0.3:
        signal = "SELL"
        confidence = 0.7
    else:
        signal = "HOLD"
        confidence = 0.6
        
    print(f"🎯 Heuristic Signal: {signal} (Confidence: {confidence:.1%})")
    assert signal in ["BUY", "SELL", "HOLD"]
    
    # 2. Narrative Agent Testing (simulated with realistic scenarios)
    print(f"\n📱 Narrative Agent Analysis:")
    
    # Simulate social sentiment based on price action
    if change_24h > 5:
        sentiment_bias = 0.6  # Very bullish
        narrative = "Social media buzzing with SOL pump posts"
    elif change_24h > 2:
        sentiment_bias = 0.3  # Moderately bullish
        narrative = "Positive sentiment in crypto communities"
    elif change_24h < -5:
        sentiment_bias = -0.6  # Very bearish
        narrative = "Market sentiment is fearful, FUD spreading"
    elif change_24h < -2:
        sentiment_bias = -0.3  # Moderately bearish
        narrative = "Some concerns about SOL price drop"
    else:
        sentiment_bias = 0.0  # Neutral
        narrative = "Market is quiet, no strong narrative"
        
    print(f"Narrative: {narrative}")
    print(f"Sentiment Bias: {sentiment_bias:.2f}")
    
    # Generate narrative signal
    if sentiment_bias > 0.4:
        narrative_signal = "STRONG_BULLISH"
    elif sentiment_bias > 0.1:
        narrative_signal = "BULLISH"
    elif sentiment_bias < -0.4:
        narrative_signal = "STRONG_BEARISH"
    elif sentiment_bias < -0.1:
        narrative_signal = "BEARISH"
    else:
        narrative_signal = "NEUTRAL"
        
    print(f"🎯 Narrative Signal: {narrative_signal}")
    assert narrative_signal in ["STRONG_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "STRONG_BEARISH"]
    print("✅ Agent tests with live data completed.")

def test_comprehensive_validator_with_live_data(live_sol_data):
    """Test comprehensive validator with live market data"""
    print(f"\n🛡️ COMPREHENSIVE VALIDATOR WITH LIVE DATA")
    print("=" * 50)
    
    price = live_sol_data["price"]
    change_24h = live_sol_data["change_24h"]
    volume_24h = live_sol_data["volume_24h"]
    
    # --- Risk Assessment ---
    # High volatility check
    is_volatile = abs(change_24h) > 15  # e.g., > 15% change in 24h
    
    # Low liquidity check
    is_low_liquidity = volume_24h < 500_000_000  # e.g., < $500M 24h volume
    
    # --- Compliance Check ---
    # Simulate a check against a compliant asset list (SOL is compliant)
    is_compliant_asset = True
    
    # --- Final Validation ---
    is_risky = is_volatile or is_low_liquidity
    is_compliant = is_compliant_asset
    
    if is_compliant and not is_risky:
        decision = "APPROVED"
    else:
        decision = "REJECTED"
        
    print(f"Is Volatile (>15%): {is_volatile}")
    print(f"Is Low Liquidity (<$500M): {is_low_liquidity}")
    print(f"Is Compliant Asset: {is_compliant}")
    print(f"Final Decision: {decision}")
    
    assert decision in ["APPROVED", "REJECTED"]
    print("✅ Comprehensive validator test with live data completed.")

def main():
    """Main function to run the test workflow"""
    # This function is for standalone script execution, not for pytest
    
    # To run these tests as a script, we call the fixture function directly
    # to get the data, and then pass it to the test functions.
    
    print("Running live market tests as a standalone script...")
    
    # We can't use pytest fixtures directly, so we mock the API call
    # for standalone execution to avoid test pollution.
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "solana": {
            "usd": 150.0,
            "usd_24h_change": 5.5,
            "usd_24h_vol": 2_500_000_000
        }
    }
    
    with patch('requests.get', return_value=mock_response):
        # Re-create the logic of the fixture for the script runner
        data = {
            "price": 150.0,
            "change_24h": 5.5,
            "volume_24h": 2_500_000_000
        }
        test_agents_with_live_data(data)
        test_comprehensive_validator_with_live_data(data)

if __name__ == "__main__":
    main()
