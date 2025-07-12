#!/usr/bin/env python3
"""
Crypto vs Meme Coin Agent Comparison
Shows how the system handles traditional crypto assets vs meme coins differently.
"""

import requests
from datetime import datetime

def test_traditional_crypto():
    """Test with traditional crypto assets"""
    print("💼 TRADITIONAL CRYPTO ANALYSIS")
    print("=" * 50)
    
    jupiter_api = "https://quote-api.jup.ag/v6"
    
    # Traditional crypto tokens
    traditional_tokens = [
        {
            'name': 'Solana',
            'mint': 'So11111111111111111111111111111111111112',
            'symbol': 'SOL'
        },
        {
            'name': 'USDC',
            'mint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
            'symbol': 'USDC'
        }
    ]
    
    for token in traditional_tokens[:1]:  # Just test SOL
        try:
            url = f"{jupiter_api}/quote"
            params = {
                'inputMint': token['mint'],
                'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                'amount': '1000000000',  # 1 SOL
                'slippageBps': '50'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                out_amount = int(data['outAmount'])
                price_impact = float(data.get('priceImpactPct', 0))
                
                price = out_amount / 1000000  # USDC has 6 decimals
                
                print(f"✅ {token['symbol']} Price: ${price:.2f} USDC")
                print(f"📈 Price Impact: {price_impact:.4f}%")
                
                # Traditional crypto agent analysis
                analyze_traditional_crypto(token['symbol'], price, price_impact)
                
        except Exception as e:
            print(f"❌ Error fetching {token['symbol']} data: {e}")

def analyze_traditional_crypto(symbol, price, price_impact):
    """Analyze traditional crypto with conservative metrics"""
    print(f"\n📊 Traditional Crypto Agent Analysis ({symbol}):")
    print("-" * 45)
    
    # Traditional metrics focus on fundamentals
    liquidity_score = 1.0 if price_impact < 0.1 else 0.8 if price_impact < 0.5 else 0.3
    stability_score = 1.0 if price_impact < 0.05 else 0.6
    institutional_grade = price_impact < 0.1
    
    print(f"   💰 Price: ${price:.2f}")
    print(f"   📊 Price Impact: {price_impact:.4f}%")
    print(f"   💧 Liquidity Score: {liquidity_score:.2f}")
    print(f"   🛡️  Stability Score: {stability_score:.2f}")
    print(f"   🏛️  Institutional Grade: {'YES' if institutional_grade else 'NO'}")
    
    # Conservative signal generation
    if liquidity_score > 0.9 and stability_score > 0.8:
        signal = "CONSERVATIVE BUY 📈"
        confidence = 0.8
    elif liquidity_score > 0.7:
        signal = "HOLD 📊"
        confidence = 0.6
    else:
        signal = "MONITOR 👁️"
        confidence = 0.4
    
    risk_level = "LOW" if price_impact < 0.1 else "MEDIUM" if price_impact < 0.5 else "HIGH"
    
    print(f"   🎯 Signal: {signal}")
    print(f"   💪 Confidence: {confidence:.1%}")
    print(f"   ⚠️  Risk: {risk_level}")
    print("   🎨 Strategy: Long-term, fundamental-based")

def test_meme_coins():
    """Test with meme coins"""
    print("\n🎪 MEME COIN ANALYSIS")
    print("=" * 50)
    
    jupiter_api = "https://quote-api.jup.ag/v6"
    
    # Meme tokens
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
        }
    ]
    
    for token in meme_tokens[:1]:  # Just test BONK
        try:
            url = f"{jupiter_api}/quote"
            params = {
                'inputMint': token['mint'],
                'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                'amount': '1000000',  # 1M tokens
                'slippageBps': '100'  # Higher slippage for memes
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                in_amount = int(data['inAmount'])
                out_amount = int(data['outAmount'])
                price_impact = float(data.get('priceImpactPct', 0))
                
                price = out_amount / 1000000 / in_amount * 1000000
                
                print(f"✅ {token['symbol']} Price: ${price:.8f} USDC")
                print(f"📈 Price Impact: {price_impact:.4f}%")
                
                # Meme coin agent analysis
                analyze_meme_coin(token['symbol'], price, price_impact)
                
        except Exception as e:
            print(f"❌ Error fetching {token['symbol']} data: {e}")

def analyze_meme_coin(symbol, price, price_impact):
    """Analyze meme coin with volatility and social metrics"""
    print(f"\n📊 Meme Coin Agent Analysis ({symbol}):")
    print("-" * 40)
    
    # Meme-specific metrics
    degen_score = min(price_impact / 2, 1.0)  # Higher impact = more degen
    moonshot_potential = 0.8 if price_impact > 1 else 0.6 if price_impact > 0.5 else 0.3
    rug_risk = price_impact / 10  # Higher impact = higher rug risk
    social_momentum = 0.7  # Simulated
    
    print(f"   💰 Price: ${price:.8f}")
    print(f"   📊 Price Impact: {price_impact:.4f}%")
    print(f"   🎲 Degen Score: {degen_score:.2f}")
    print(f"   🚀 Moonshot Potential: {moonshot_potential:.2f}")
    print(f"   🚨 Rug Risk: {rug_risk:.2f}")
    print(f"   📱 Social Momentum: {social_momentum:.2f}")
    
    # Aggressive signal generation
    if moonshot_potential > 0.7 and rug_risk < 0.3 and social_momentum > 0.6:
        signal = "DEGEN BUY 🚀"
        confidence = 0.75
    elif moonshot_potential > 0.5 and rug_risk < 0.5:
        signal = "YOLO 🎲"
        confidence = 0.6
    elif rug_risk > 0.7:
        signal = "AVOID - RUG RISK ❌"
        confidence = 0.9
    else:
        signal = "WATCH FOR PUMP 👀"
        confidence = 0.5
    
    risk_level = "EXTREME" if rug_risk > 0.7 else "HIGH" if rug_risk > 0.3 else "MEDIUM"
    
    print(f"   🎯 Signal: {signal}")
    print(f"   💪 Confidence: {confidence:.1%}")
    print(f"   ⚠️  Risk: {risk_level}")
    print("   🎨 Strategy: Short-term, momentum-based")

def main():
    """Compare traditional crypto vs meme coin analysis"""
    print("🔄 CRYPTO vs MEME COIN AGENT COMPARISON")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Comparing how agents handle different asset types")
    print()
    
    # Test traditional crypto
    test_traditional_crypto()
    
    # Test meme coins
    test_meme_coins()
    
    # Summary comparison
    print("\n📋 AGENT STRATEGY COMPARISON")
    print("=" * 60)
    print("💼 TRADITIONAL CRYPTO AGENTS:")
    print("   • Focus: Liquidity, stability, fundamentals")
    print("   • Risk: Conservative, institutional-grade")
    print("   • Signals: Long-term, steady growth")
    print("   • Price Impact Tolerance: <0.1% preferred")
    print("   • Strategy: DCA, HODLing, portfolio allocation")
    
    print("\n🎪 MEME COIN AGENTS:")
    print("   • Focus: Momentum, social sentiment, volatility")
    print("   • Risk: High risk, high reward")
    print("   • Signals: Short-term, pump detection")
    print("   • Price Impact Tolerance: >1% acceptable")
    print("   • Strategy: Quick entry/exit, social momentum")
    
    print("\n🎯 KEY DIFFERENCES:")
    print("   • Time Horizon: Long-term vs Short-term")
    print("   • Risk Tolerance: Low vs High")
    print("   • Data Sources: On-chain vs Social + On-chain")
    print("   • Signal Frequency: Daily vs Real-time")
    print("   • Position Sizing: Larger vs Smaller")

if __name__ == "__main__":
    main()
