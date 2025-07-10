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

def test_meme_narrative_simulation():
    """Simulate narrative agent with mock meme coin social data"""
    print(f"\n📱 Testing Meme Narrative Agent (Simulated):")
    print("-" * 50)
    
    # Mock social media posts specifically about meme coins
    mock_meme_posts = [
        "BONK is absolutely pumping today! This dog coin is going to the moon 🚀🐕",
        "WIF (dogwifhat) looking sus... might be time to take profits and run",
        "PEPE season is back! Just aped into a fat bag, let's go frogs 🐸💎", 
        "Meme coins are getting wild again, pump.fun launching 50 new coins per hour",
        "These Solana meme coins are pure degeneracy but I can't stop buying them 🎪",
        "Got rugged by another dog coin... why do I keep falling for this 💀",
        "WIF chart looking bullish AF! Break above resistance incoming 📈",
        "BONK community is unhinged in the best way, diamond handing this one 💎🙌"
    ]
    
    sentiments = []
    meme_signals = []
    
    for i, post in enumerate(mock_meme_posts):
        sentiment = calculate_meme_sentiment(post)
        sentiments.append(sentiment)
        
        # Extract meme-specific signals
        meme_signal = extract_meme_signals(post)
        meme_signals.append(meme_signal)
        
        print(f"Post {i+1}: {sentiment:.2f} | {meme_signal} | {post[:60]}...")
    
    avg_sentiment = sum(sentiments) / len(sentiments)
    bullish_count = sum(1 for s in meme_signals if 'BULL' in s)
    bearish_count = sum(1 for s in meme_signals if 'BEAR' in s)
    
    print(f"\n📊 Meme Sentiment Analysis:")
    print(f"Average Sentiment: {avg_sentiment:.2f}")
    print(f"Sentiment Range: {min(sentiments):.2f} to {max(sentiments):.2f}")
    print(f"Bullish Signals: {bullish_count}")
    print(f"Bearish Signals: {bearish_count}")
    
    # Generate narrative signal
    if avg_sentiment > 0.3 or bullish_count > bearish_count + 2:
        narrative_signal = "MEME SEASON 🚀"
    elif avg_sentiment < -0.3 or bearish_count > bullish_count + 2:
        narrative_signal = "MEME WINTER ❄️"
    else:
        narrative_signal = "MEME CHOP 🌊"
    
    print(f"🎯 Meme Narrative Signal: {narrative_signal}")
    return narrative_signal, avg_sentiment

def extract_meme_signals(text):
    """Extract meme-specific trading signals from text"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['pump', 'moon', 'bullish', 'break above']):
        return "BULL"
    elif any(word in text_lower for word in ['dump', 'sus', 'rug', 'take profits']):
        return "BEAR"
    elif any(word in text_lower for word in ['diamond hand', 'hodl', 'fat bag']):
        return "HOLD"
    else:
        return "NEUTRAL"

def calculate_meme_sentiment(text):
    """Calculate sentiment specific to meme coin culture"""
    bullish_meme_words = [
        'pump', 'moon', '🚀', '💎', 'diamond', 'bullish', 'break above',
        'aped', 'fat bag', 'season', 'going', 'unhinged', 'best way'
    ]
    
    bearish_meme_words = [
        'sus', 'rug', 'rugged', 'take profits', 'run', 'degeneracy', 
        'wild', 'falling', '💀', 'can\'t stop'
    ]
    
    text_lower = text.lower()
    
    bullish_count = sum(1 for word in bullish_meme_words if word in text_lower)
    bearish_count = sum(1 for word in bearish_meme_words if word in text_lower)
    
    # Factor in meme emojis
    rocket_count = text.count('🚀') + text.count('🌙')
    diamond_count = text.count('💎') + text.count('🙌')
    negative_count = text.count('💀') + text.count('❄️')
    
    total_signals = bullish_count + bearish_count + rocket_count + diamond_count + negative_count
    
    if total_signals == 0:
        return 0.0
    
    sentiment = (bullish_count + rocket_count + diamond_count - bearish_count - negative_count) / max(len(text.split()), 1)
    return sentiment

def main():
    """Run comprehensive meme coin live data testing"""
    print("� MEME COIN LIVE DATA AGENT TESTING")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Focus: Live meme coin prices and social sentiment")
    print()
    
    # Test 1: Live meme coin market data
    meme_success = test_meme_coin_live_data()
    
    # Test 2: Meme narrative analysis (simulated)
    narrative_signal, avg_sentiment = test_meme_narrative_simulation()
    
    # Combined analysis
    if meme_success:
        print(f"\n🧠 COMBINED MEME AGENT ANALYSIS:")
        print("=" * 50)
        print("✅ Meme coin data: LIVE (Jupiter API)")
        print("✅ Sentiment data: SIMULATED")
        print(f"📊 Narrative bias: {narrative_signal}")
        print(f"📈 Market analysis: Based on live meme coin prices")
        print(f"🎯 Sentiment score: {avg_sentiment:.2f}")
        
        # This is where the real system would combine signals
        print(f"\n💡 Next Steps for Full Meme Coin Live Trading:")
        print("1. ✅ Jupiter API integration working for meme coins")
        print("2. 🔄 Add pump.fun WebSocket for new token detection")
        print("3. 🔄 Add Twitter API for real meme coin sentiment")
        print("4. 🔄 Add Telegram group monitoring for meme communities")
        print("5. 🔄 Implement social momentum scoring")
        print("6. 🔄 Add holder analytics from Solana RPC")
        print("7. 🔄 Run agents continuously with live meme feeds")
        
        print(f"\n🎪 MEME COIN SYSTEM STATUS:")
        print("✅ Basic meme coin price fetching: WORKING")
        print("✅ Meme-specific risk analysis: IMPLEMENTED")
        print("✅ Social sentiment simulation: WORKING")
        print("🔄 Real-time social feeds: PENDING")
        print("🔄 pump.fun integration: PENDING")
        print("🔄 Automated trading: PENDING")
        
    else:
        print("\n❌ Live meme coin data failed - check network/API access")
        print("Falling back to simulated narrative analysis only...")

if __name__ == "__main__":
    main()
