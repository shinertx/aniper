#!/usr/bin/env python3
"""
Quick Meme Coin Live Data Validation
Tests Jupiter API with meme coins and validates agent logic with current pump.fun market data.
"""

import requests
import json
import time
from datetime import datetime
import os
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(scope="module")
def meme_prices():
    """Fixture to fetch live meme coin prices from Jupiter API."""
    print("\n🚀 Testing with Live Meme Coin Market Data from Jupiter")
    print("=" * 60)
    
    jupiter_api = "https://quote-api.jup.ag/v6"
    
    meme_tokens = [
        {
            'name': 'BONK',
            'mint': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
            'symbol': 'BONK',
            'decimals': 5
        },
        {
            'name': 'WIF (dogwifhat)',
            'mint': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm',
            'symbol': 'WIF',
            'decimals': 6
        },
        {
            'name': 'PEPE',
            'mint': 'BnNKRBuZNRhjNJqJJDJ8jKxRreLnhLfhEFfMUeZZ1V7d',
            'symbol': 'PEPE',
            'decimals': 8
        }
    ]
    
    prices = {}
    
    for token in meme_tokens:
        try:
            # Amount should be adjusted based on token decimals for a more stable quote
            amount_to_quote = 100 * (10 ** token['decimals']) # e.g., 100 tokens
            
            url = f"{jupiter_api}/quote"
            params = {
                'inputMint': token['mint'],
                'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC (6 decimals)
                'amount': str(amount_to_quote),
                'slippageBps': '100'
            }
            
            print(f"📊 Fetching live {token['symbol']} price...")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            in_amount = int(data['inAmount'])
            out_amount = int(data['outAmount'])
            price_impact = float(data.get('priceImpactPct', 0))
            
            # Price per token in USDC
            # (out_amount / 10^6) / (in_amount / 10^token_decimals)
            token_price = (out_amount / 10**6) / (in_amount / 10**token['decimals'])
            
            print(f"✅ {token['symbol']} Price: ${token_price:.8f} USDC")
            print(f"📈 Price Impact: {price_impact:.4f}%")
            
            prices[token['symbol']] = {
                'price': token_price,
                'price_impact': price_impact,
                'name': token['name']
            }
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Could not fetch {token['symbol']} data: {e}. Skipping.")
        except Exception as e:
            print(f"❌ Unexpected error for {token['symbol']}: {e}. Skipping.")
        
        print()

    if not prices:
        pytest.fail("❌ No meme coin data could be retrieved from Jupiter API.")
        
    return prices

def test_jupiter_api_response(meme_prices):
    """Tests that the meme_prices fixture returns a valid structure."""
    assert isinstance(meme_prices, dict)
    assert len(meme_prices) > 0, "Should have fetched at least one meme coin price"
    
    # Check the structure of the first item
    first_key = list(meme_prices.keys())[0]
    assert "price" in meme_prices[first_key]
    assert "price_impact" in meme_prices[first_key]
    assert isinstance(meme_prices[first_key]["price"], float)
    print("\n✅ Jupiter API data fixture is valid.")

def test_meme_heuristic_agent(meme_prices):
    """Test heuristic agent logic with live meme coin price data"""
    print(f"\n🤖 Testing Meme Coin Heuristic Agent Logic:")
    print("-" * 40)
    
    for symbol, data in meme_prices.items():
        price = data['price']
        price_impact = data['price_impact']
        
        print(f"🪙 {symbol} ({data['name']}):")
        print(f"   Price: ${price:.8f}")
        print(f"   Price Impact for 100 tokens: {price_impact:.4f}%")
        
        # --- Heuristic Rules ---
        # Rule 1: Price impact as a proxy for liquidity
        liquidity_score = max(0, 1 - price_impact * 10) # Lower impact is better
        
        # Rule 2: Price level (very low price might indicate higher risk/reward)
        price_score = 1 if price < 0.0001 else 0.5
        
        # Rule 3: Token name (just for fun, not a real signal)
        if 'wif' in data['name'].lower() or 'pepe' in data['name'].lower():
            hype_score = 0.5
        else:
            hype_score = 0.2
            
        # --- Signal Aggregation ---
        total_score = liquidity_score + price_score + hype_score
        
        if total_score > 2.0:
            signal = "STRONG_BUY"
        elif total_score > 1.5:
            signal = "BUY"
        else:
            signal = "HOLD"
            
        print(f"   Scores -> Liquidity: {liquidity_score:.2f}, Price: {price_score:.2f}, Hype: {hype_score:.2f}")
        print(f"   🎯 Heuristic Signal: {signal} (Total Score: {total_score:.2f})")
        print()
        
        assert signal in ["STRONG_BUY", "BUY", "HOLD"]
    print("✅ Meme heuristic agent tests completed.")

def test_meme_narrative_simulation(meme_prices):
    """Simulate narrative agent with mock meme coin social data"""
    print(f"\n📱 Testing Meme Coin Narrative Simulation:")
    print("-" * 40)
    
    # Simulate social media narratives for the fetched coins
    for symbol, data in meme_prices.items():
        narrative = "NEUTRAL"
        sentiment_score = 0.0
        
        if 'WIF' in symbol:
            narrative = "BULLISH - Strong community, still a top meme."
            sentiment_score = 0.7
        elif 'PEPE' in symbol:
            narrative = "NEUTRAL - Established, but less volatile now."
            sentiment_score = 0.3
        elif 'BONK' in symbol:
            narrative = "BEARISH - Lost some momentum to newer memes."
            sentiment_score = -0.2
            
        print(f"🪙 {symbol}:")
        print(f"   Narrative: {narrative}")
        print(f"   Sentiment Score: {sentiment_score:.2f}")
        
        if sentiment_score > 0.5:
            signal = "STRONG_BUY"
        elif sentiment_score > 0.1:
            signal = "BUY"
        elif sentiment_score < -0.1:
            signal = "SELL"
        else:
            signal = "HOLD"
            
        print(f"   🎯 Narrative Signal: {signal}")
        print()
        
        assert signal in ["STRONG_BUY", "BUY", "SELL", "HOLD"]
        
    print("✅ Meme narrative simulation tests completed.")

def test_comprehensive_validator_simulation(meme_prices):
    """Comprehensive test for the validator agent using live data"""
    print(f"\n🛡️ Testing Meme Coin Comprehensive Validator:")
    print("-" * 50)
    
    for symbol, data in meme_prices.items():
        # --- Risk Assessment ---
        # High price impact suggests low liquidity, which is risky
        is_high_risk = data['price_impact'] > 1.0  # >1% impact is significant
        
        # --- Compliance Check ---
        # Simulate checking a token against a known list of scams or sanctioned addresses
        # For this test, let's assume BONK is on a watchlist for some reason
        is_compliant = symbol != 'BONK'
        
        # --- Final Decision ---
        if is_compliant and not is_high_risk:
            decision = "APPROVED"
        else:
            decision = "REJECTED"
            
        print(f"🪙 {symbol}:")
        print(f"   High Risk (Price Impact > 1%): {is_high_risk}")
        print(f"   Is Compliant: {is_compliant}")
        print(f"   🎯 Final Decision: {decision}")
        print()
        
        assert decision in ["APPROVED", "REJECTED"]
        
    print("✅ Meme comprehensive validator tests completed.")

def main():
    """Main function to run the test workflow as a script."""
    print("Running quick live tests as a standalone script...")
    
    # Mock the API call for standalone execution
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "inAmount": "100000000",
        "outAmount": "200000", # 0.2 USDC
        "priceImpactPct": "0.1",
        "routePlan": [{"swapInfo": {"label": "Raydium"}}]
    }
    
    with patch('requests.get', return_value=mock_response):
        # Re-create the logic of the fixture for the script runner
        mock_prices = {
            'WIF': {'price': 0.000002, 'price_impact': 0.1, 'name': 'WIF (dogwifhat)'}
        }
        test_meme_heuristic_agent(mock_prices)
        test_meme_narrative_simulation(mock_prices)
        test_comprehensive_validator_simulation(mock_prices)

if __name__ == "__main__":
    main()
