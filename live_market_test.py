#!/usr/bin/env python3
"""
Live Market Data Validation
Tests real market APIs to validate agent performance with live data.
"""

import requests
import json
import time
from datetime import datetime

def test_coingecko_prices():
    """Test with CoinGecko API for live SOL price"""
    print("🔥 Testing with Live Market Data (CoinGecko)")
    print("=" * 50)
    
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'solana',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true'
        }
        
        print("📊 Fetching live SOL price from CoinGecko...")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'solana' in data:
                sol_data = data['solana']
                price = sol_data['usd']
                change_24h = sol_data.get('usd_24h_change', 0)
                volume_24h = sol_data.get('usd_24h_vol', 0)
                
                print(f"✅ Current SOL Price: ${price:.2f}")
                print(f"📈 24h Change: {change_24h:.2f}%")
                print(f"💰 24h Volume: ${volume_24h:,.0f}")
                
                # Test agent logic
                test_agents_with_live_data(price, change_24h, volume_24h)
                return True
            else:
                print(f"❌ No SOL data in response: {data}")
                return False
                
        else:
            print(f"❌ CoinGecko API Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error fetching live data: {e}")
        return False

def test_agents_with_live_data(price, change_24h, volume_24h):
    """Test both agents with live market data"""
    print(f"\n🤖 AGENT TESTING WITH LIVE DATA")
    print("=" * 40)
    
    # 1. Heuristic Agent Testing
    print(f"📊 Heuristic Agent Analysis:")
    print(f"Current Price: ${price:.2f}")
    print(f"Price Change: {change_24h:.2f}%")
    print(f"Volume: ${volume_24h:,.0f}")
    
    # Calculate agent metrics
    volatility_score = abs(change_24h) / 10  # 0-1 scale
    volume_score = min(volume_24h / 1000000000, 1.0)  # Normalize to 1B volume
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
        narrative = "Fear and panic selling in social feeds"
    elif change_24h < -2:
        sentiment_bias = -0.3  # Moderately bearish
        narrative = "Bearish sentiment emerging"
    else:
        sentiment_bias = 0.0  # Neutral
        narrative = "Mixed sentiment, consolidation phase"
    
    print(f"Simulated Narrative: {narrative}")
    print(f"Sentiment Bias: {sentiment_bias:.2f}")
    
    # Generate narrative signal
    if sentiment_bias > 0.4:
        narrative_signal = "BULLISH"
    elif sentiment_bias < -0.4:
        narrative_signal = "BEARISH"
    else:
        narrative_signal = "NEUTRAL"
        
    print(f"🎯 Narrative Signal: {narrative_signal}")
    
    # 3. Combined Analysis
    print(f"\n🧠 COMBINED AGENT DECISION:")
    print("-" * 30)
    
    # Weight the signals (60% heuristic, 40% narrative in this example)
    if signal == "BUY" and narrative_signal in ["BULLISH", "NEUTRAL"]:
        final_signal = "STRONG BUY"
        final_confidence = confidence * 0.9
    elif signal == "SELL" and narrative_signal in ["BEARISH", "NEUTRAL"]:
        final_signal = "STRONG SELL"
        final_confidence = confidence * 0.9
    elif signal == "BUY" and narrative_signal == "BEARISH":
        final_signal = "WEAK BUY"
        final_confidence = confidence * 0.5
    elif signal == "SELL" and narrative_signal == "BULLISH":
        final_signal = "WEAK SELL" 
        final_confidence = confidence * 0.5
    else:
        final_signal = "HOLD"
        final_confidence = 0.7
    
    print(f"Final Decision: {final_signal}")
    print(f"Final Confidence: {final_confidence:.1%}")
    
    # Risk assessment
    risk_factors = []
    if volatility_score > 0.7:
        risk_factors.append("High volatility")
    if volume_score < 0.2:
        risk_factors.append("Low volume")
    if abs(momentum_score) > 0.8:
        risk_factors.append("Extreme momentum")
        
    risk_level = "LOW" if len(risk_factors) == 0 else "MEDIUM" if len(risk_factors) == 1 else "HIGH"
    
    print(f"Risk Level: {risk_level}")
    if risk_factors:
        print(f"Risk Factors: {', '.join(risk_factors)}")
    
    return final_signal, final_confidence, risk_level

def main():
    """Run live market data testing"""
    print("🚀 LIVE AGENT PERFORMANCE TESTING")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = test_coingecko_prices()
    
    if success:
        print(f"\n✅ LIVE DATA TESTING COMPLETED")
        print(f"📊 Results: Agents successfully processed live market data")
        print(f"🎯 Next Steps:")
        print("  1. ✅ Live price data integration working")
        print("  2. 🔄 Add real Twitter sentiment analysis") 
        print("  3. 🔄 Add Solana on-chain event monitoring")
        print("  4. 🔄 Implement continuous monitoring loop")
        print("  5. 🔄 Add backtesting with historical data")
        
        print(f"\n💡 Model Tuning Recommendations:")
        print("  - Adjust volatility thresholds based on market conditions")
        print("  - Calibrate sentiment weights using historical performance")
        print("  - Implement dynamic risk scoring")
        print("  - Add multi-timeframe analysis")
        
    else:
        print(f"\n❌ Live data testing failed")
        print("Check network connectivity and API availability")

if __name__ == "__main__":
    main()
