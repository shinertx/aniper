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

def test_meme_coin_live_data():
    """Test with live meme coin data from Jupiter"""
    print("� Testing with Live Meme Coin Market Data")
    print("=" * 50)
    
    jupiter_api = "https://quote-api.jup.ag/v6"
    
    # Popular meme coin addresses (these are real Solana meme tokens)
    meme_tokens = [
        {
            'name': 'BONK',
            'mint': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
            'symbol': 'BONK'
        },
        {
            'name': 'WIF (dogwifhat)',
            'mint': 'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm',
            'symbol': 'WIF'
        },
        {
            'name': 'PEPE',
            'mint': 'BnNKRBuZNRhjNJqJJDJ8jKxRreLnhLfhEFfMUeZZ1V7d',
            'symbol': 'PEPE'
        }
    ]
    
    successful_tests = 0
    meme_prices = {}
    
    for token in meme_tokens:
        try:
            url = f"{jupiter_api}/quote"
            params = {
                'inputMint': token['mint'],  # Meme token
                'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC  
                'amount': '1000000',  # 1M tokens (adjust for token decimals)
                'slippageBps': '100'  # Higher slippage for meme coins
            }
            
            print(f"📊 Fetching live {token['symbol']} price...")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract price information
                in_amount = int(data['inAmount'])
                out_amount = int(data['outAmount'])
                price_impact = float(data.get('priceImpactPct', 0))
                
                # Calculate price per token in USDC
                token_price = out_amount / 1000000 / in_amount * 1000000  # Adjust for decimals
                
                print(f"✅ {token['symbol']} Price: ${token_price:.8f} USDC")
                print(f"📈 Price Impact: {price_impact:.4f}%")
                print(f"🎯 Route: {data.get('routePlan', [{}])[0].get('swapInfo', {}).get('label', 'Unknown')}")
                
                meme_prices[token['symbol']] = {
                    'price': token_price,
                    'price_impact': price_impact,
                    'name': token['name']
                }
                
                successful_tests += 1
                
            else:
                print(f"❌ Jupiter API Error for {token['symbol']}: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Error fetching {token['symbol']} data: {e}")
        
        print()
    
    if successful_tests > 0:
        # Test agent logic with meme coin data
        test_meme_heuristic_agent(meme_prices)
        return True
    else:
        print("❌ No successful meme coin data retrieved")
        return False
            
            return True
            
        else:
            print(f"❌ Jupiter API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error fetching live data: {e}")
        return False

def test_meme_heuristic_agent(meme_prices):
    """Test heuristic agent logic with live meme coin price data"""
    print(f"\n🤖 Testing Meme Coin Agent Logic:")
    print("-" * 40)
    
    for symbol, data in meme_prices.items():
        print(f"\n🪙 Analyzing {symbol} ({data['name']}):")
        
        price = data['price']
        price_impact = data['price_impact']
        
        # Simulate meme coin specific metrics
        # In real system, this would come from on-chain data and social monitoring
        volatility = price_impact * 10  # Meme coins are more volatile
        liquidity_depth = 100 - (price_impact * 1000)  # Lower liquidity = higher impact
        
        # Meme coin signals
        signals = []
        risk_factors = []
        
        # Price impact analysis (critical for meme coins)
        if price_impact < 0.5:
            signals.append("Good liquidity")
        elif price_impact < 2.0:
            signals.append("Moderate liquidity risk")
            risk_factors.append("Medium price impact")
        else:
            signals.append("Low liquidity - HIGH RISK")
            risk_factors.append("Extreme price impact")
        
        # Volatility assessment
        if volatility > 20:
            signals.append("High volatility - potential moonshot")
            risk_factors.append("Extreme volatility")
        elif volatility > 5:
            signals.append("Moderate volatility")
        else:
            signals.append("Low volatility - less meme potential")
        
        # Generate meme-specific trading signal
        if price_impact < 1 and volatility > 10:
            signal = "DEGEN BUY 🚀"
            confidence = 0.8
        elif price_impact < 2 and volatility > 5:
            signal = "CAUTIOUS BUY 📈"
            confidence = 0.6
        elif price_impact > 5:
            signal = "AVOID - RUG RISK ❌"
            confidence = 0.9
        else:
            signal = "WATCH 👀"
            confidence = 0.5
        
        # Risk assessment for meme coins
        risk_score = min((price_impact / 5) + (len(risk_factors) * 0.2), 1.0)
        
        print(f"   💰 Price: ${price:.8f} USDC")
        print(f"   📊 Price Impact: {price_impact:.4f}%")
        print(f"   🎢 Volatility: {volatility:.2f}%")
        print(f"   💧 Liquidity Depth: {liquidity_depth:.1f}%")
        print(f"   🎯 Signals: {', '.join(signals)}")
        print(f"   🚨 Risk Factors: {', '.join(risk_factors) if risk_factors else 'None'}")
        print(f"   📈 Agent Decision: {signal}")
        print(f"   💪 Confidence: {confidence:.1%}")
        print(f"   ⚠️  Risk Score: {risk_score:.2f} ({'EXTREME' if risk_score > 0.8 else 'HIGH' if risk_score > 0.6 else 'MEDIUM' if risk_score > 0.3 else 'LOW'})")
    
    return True

def test_narrative_simulation():
    """Simulate narrative agent with mock social data"""
    print(f"\n📱 Testing Narrative Agent (Simulated):")
    print("-" * 40)
    
    # Mock social media posts (representing what we'd get from Twitter)
    mock_posts = [
        "SOL is absolutely pumping today! New ATH incoming 🚀🌙",
        "Market looking bearish, time to take profits on SOL positions",
        "Solana network congestion issues again... not good for price",
        "Major DeFi protocol launching on Solana next week, bullish!",
        "SOL chart looking good, break above $200 would be massive"
    ]
    
    sentiments = []
    for i, post in enumerate(mock_posts):
        sentiment = calculate_sentiment(post)
        sentiments.append(sentiment)
        print(f"Post {i+1}: {sentiment:.2f} | {post[:50]}...")
    
    avg_sentiment = sum(sentiments) / len(sentiments)
    print(f"\n📊 Sentiment Analysis:")
    print(f"Average Sentiment: {avg_sentiment:.2f}")
    print(f"Sentiment Range: {min(sentiments):.2f} to {max(sentiments):.2f}")
    
    # Generate narrative signal
    if avg_sentiment > 0.3:
        narrative_signal = "BULLISH"
    elif avg_sentiment < -0.3:
        narrative_signal = "BEARISH"
    else:
        narrative_signal = "NEUTRAL"
    
    print(f"🎯 Narrative Signal: {narrative_signal}")
    return narrative_signal, avg_sentiment

def calculate_sentiment(text):
    """Simple sentiment calculation"""
    bullish_words = ['pump', 'moon', 'bullish', 'ath', 'massive', 'good', 'launch']
    bearish_words = ['bearish', 'dump', 'crash', 'issues', 'congestion', 'bad']
    
    text_lower = text.lower()
    bullish_count = sum(1 for word in bullish_words if word in text_lower)
    bearish_count = sum(1 for word in bearish_words if word in text_lower)
    
    return (bullish_count - bearish_count) / max(len(text.split()), 1)

def main():
    """Run comprehensive live data testing"""
    print("🔥 LIVE DATA AGENT TESTING")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Live market data
    jupiter_success = test_jupiter_live_data()
    
    # Test 2: Narrative analysis (simulated)
    narrative_signal, avg_sentiment = test_narrative_simulation()
    
    # Combined analysis
    if jupiter_success:
        print(f"\n🧠 COMBINED AGENT ANALYSIS:")
        print("=" * 40)
        print("✅ Market data: LIVE")
        print("✅ Sentiment data: SIMULATED")
        print(f"📊 Narrative bias: {narrative_signal}")
        print(f"📈 Market analysis: Based on live SOL prices")
        
        # This is where the real system would combine signals
        print(f"\n💡 Next Steps for Full Live Testing:")
        print("1. ✅ Jupiter API integration working")
        print("2. 🔄 Add Twitter API for real sentiment data")
        print("3. 🔄 Add Solana WebSocket for real-time events")
        print("4. 🔄 Run agents continuously with live feeds")
        
    else:
        print("\n❌ Live market data failed - check network/API access")

if __name__ == "__main__":
    main()
