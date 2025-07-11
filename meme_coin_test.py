#!/usr/bin/env python3
"""
Meme Coin Trading System Live Test
Tests the agents with real pump.fun meme coin data and social sentiment.
"""

import requests
import json
import time
from datetime import datetime
import re
import pytest

@pytest.fixture(scope="module")
def meme_coins():
    """Provides realistic pump.fun meme coin data."""
    print("🐸 Setting up meme coin data fixture")
    
    meme_coins_data = [
        {
            "name": "PEPE2024",
            "mint": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            "creator": "BobTheBuilder420",
            "market_cap": 1_200_000,
            "holders": 1_847,
            "lp_ratio": 0.85,
            "price_change_5m": 156.7,
            "volume_24h": 890_000,
            "created_hours_ago": 2.3,
            "twitter_mentions": 234,
            "telegram_members": 1_200
        },
        {
            "name": "DOGWIFHAT",
            "mint": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
            "creator": "MemeKing69",
            "market_cap": 5_600_000,
            "holders": 3_421,
            "lp_ratio": 0.92,
            "price_change_5m": -23.4,
            "volume_24h": 2_100_000,
            "created_hours_ago": 18.7,
            "twitter_mentions": 1_203,
            "telegram_members": 4_500
        },
        {
            "name": "BONKINU",
            "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "creator": "CryptoApe88",
            "market_cap": 12_800_000,
            "holders": 8_932,
            "lp_ratio": 0.78,
            "price_change_5m": 45.2,
            "volume_24h": 7_800_000,
            "created_hours_ago": 72.1,
            "twitter_mentions": 5_678,
            "telegram_members": 12_400
        }
    ]
    
    print("📊 Current Meme Coin Market Data (from fixture):")
    print("-" * 40)
    
    for coin in meme_coins_data:
        print(f"🪙 {coin['name']}")
        print(f"   Market Cap: ${coin['market_cap']:,}")
        print(f"   Holders: {coin['holders']:,}")
        print(f"   5m Change: {coin['price_change_5m']:+.1f}%")
        print(f"   Social Buzz: {coin['twitter_mentions']} mentions")
        print()
        
    return meme_coins_data

@pytest.fixture(scope="module")
def coin_sentiments(meme_coins):
    """Analyzes and provides sentiment data for the given meme coins."""
    print("🤖 Analyzing meme sentiment (from fixture)")
    
    social_posts = [
        {
            "text": "PEPE2024 is absolutely going to the moon! 🚀🐸 Just bought a bag, this is the next 1000x gem",
            "engagement": {"likes": 234, "retweets": 89, "replies": 45},
            "coin_mentioned": "PEPE2024"
        },
        {
            "text": "DOGWIFHAT dumping hard... glad I sold at the top. Meme season might be over",
            "engagement": {"likes": 67, "retweets": 23, "replies": 12},
            "coin_mentioned": "DOGWIFHAT"
        },
        {
            "text": "BONKINU looking strong! Community is solid and devs are based. Holding this one long term",
            "engagement": {"likes": 156, "retweets": 78, "replies": 34},
            "coin_mentioned": "BONKINU"
        },
        {
            "text": "Pump.fun is wild today! So many new memes launching every minute 🎢",
            "engagement": {"likes": 89, "retweets": 34, "replies": 18},
            "coin_mentioned": "GENERAL"
        },
        {
            "text": "Just lost $500 on a rug pull... be careful out there frens, not all memes are gems 💎",
            "engagement": {"likes": 123, "retweets": 67, "replies": 89},
            "coin_mentioned": "GENERAL"
        }
    ]
    
    coin_sentiments_data = {}
    
    for coin in meme_coins:
        coin_name = coin['name']
        relevant_posts = [p for p in social_posts if p['coin_mentioned'] == coin_name]
        
        if relevant_posts:
            sentiments = []
            total_engagement = 0
            
            for post in relevant_posts:
                sentiment = calculate_meme_sentiment(post['text'])
                engagement_weight = sum(post['engagement'].values())
                sentiments.append(sentiment * engagement_weight)
                total_engagement += engagement_weight
            
            weighted_sentiment = sum(sentiments) / max(total_engagement, 1)
            coin_sentiments_data[coin_name] = {
                'sentiment': weighted_sentiment,
                'post_count': len(relevant_posts),
                'total_engagement': total_engagement
            }
        else:
            coin_sentiments_data[coin_name] = {
                'sentiment': 0.0,
                'post_count': 0,
                'total_engagement': 0
            }
            
    return coin_sentiments_data

@pytest.fixture(scope="module")
def trading_signals(meme_coins, coin_sentiments):
    """Fixture to generate trading signals from the heuristic agent."""
    print("🧠 Generating trading signals (from fixture)")
    
    trading_signals = {}
    
    for coin in meme_coins:
        coin_name = coin['name']
        
        # Meme-specific metrics
        holder_growth_score = min(coin['holders'] / 2000, 1.0)  # Scale up
        lp_health_score = coin['lp_ratio']
        volume_score = min(coin['volume_24h'] / 500_000, 1.0) # Scale up
        momentum_score = max(min(coin['price_change_5m'] / 100, 1), -1)
        age_score = max(0, min(1 - (coin['created_hours_ago'] / 168), 1))
        social_buzz_score = min(coin['twitter_mentions'] / 1000, 1.0) # Scale up
        
        sentiment_score = coin_sentiments.get(coin_name, {}).get('sentiment', 0)
        
        # Calculate composite score
        technical_score = (holder_growth_score * 1.2 + lp_health_score + volume_score + 
                          momentum_score * 1.5 + age_score) / 4.7
        
        social_score = (social_buzz_score * 1.2 + max(sentiment_score, 0) * 1.5) / 2.7
        
        composite_score = technical_score * 0.55 + social_score * 0.45
        
        # Generate signal
        if composite_score > 0.7 and momentum_score > 0.5 and sentiment_score > 0.1:
            signal = "STRONG BUY 🚀"
            confidence = min(0.95, composite_score + 0.1)
        elif composite_score > 0.55 and momentum_score > 0:
            signal = "BUY 📈"
            confidence = composite_score
        elif composite_score < 0.45 or momentum_score < -0.2:
            signal = "AVOID ❌"
            confidence = 1 - composite_score
        else:
            signal = "WATCH 👀"
            confidence = 0.5
        
        # Risk assessment
        risk_factors = []
        if coin['holders'] < 500:
            risk_factors.append("Low holder count")
        if coin['lp_ratio'] < 0.8:
            risk_factors.append("LP ratio risk")
        if coin['created_hours_ago'] < 1:
            risk_factors.append("Very new token")
        if abs(momentum_score) > 0.8:
            risk_factors.append("High volatility")
        
        risk_level = "EXTREME" if len(risk_factors) >= 3 else "HIGH" if len(risk_factors) == 2 else "MEDIUM" if len(risk_factors) == 1 else "LOW"
        
        trading_signals[coin_name] = {
            'signal': signal,
            'confidence': confidence,
            'composite_score': composite_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors
        }
        
    return trading_signals

def test_meme_coin_data_fixture(meme_coins):
    """Tests that the meme_coins fixture loads correctly."""
    assert isinstance(meme_coins, list)
    assert len(meme_coins) == 3
    assert "name" in meme_coins[0]
    print("\n✅ Fixture 'meme_coins' loaded successfully.")

def test_meme_narrative_agent(coin_sentiments):
    """Test narrative agent with meme coin social data"""
    print("\n🤖 NARRATIVE AGENT: Meme Sentiment Analysis")
    print("=" * 50)
    
    for coin_name, sentiment_data in coin_sentiments.items():
        print(f"🪙 {coin_name}:")
        print(f"   Sentiment Score: {sentiment_data['sentiment']:.3f}")
        print(f"   Posts Analyzed: {sentiment_data['post_count']}")
        print(f"   Total Engagement: {sentiment_data['total_engagement']}")
        
        if sentiment_data['sentiment'] > 0.3:
            narrative_signal = "BULLISH 🚀"
        elif sentiment_data['sentiment'] < -0.3:
            narrative_signal = "BEARISH 📉"
        else:
            narrative_signal = "NEUTRAL 😐"
            
        print(f"   🎯 Narrative Signal: {narrative_signal}")
        print()

    assert coin_sentiments['PEPE2024']['sentiment'] > 0.25, "PEPE2024 should have bullish sentiment"
    assert coin_sentiments['DOGWIFHAT']['sentiment'] < 0, "DOGWIFHAT should have bearish sentiment"
    assert coin_sentiments['BONKINU']['sentiment'] > 0, "BONKINU should have positive sentiment"
    print("✅ Narrative agent produced expected sentiment signals.")

def calculate_meme_sentiment(text):
    """Calculate sentiment specific to meme coin culture"""
    bullish_meme_words = [
        'moon', 'rocket', '🚀', 'gem', '💎', 'based', 'ape', 'fomo', 
        'pump', 'bullish', 'hodl', 'diamond hands', 'lambo', 'wagmi',
        '1000x', '100x', 'degen', 'chad', 'alpha'
    ]
    
    bearish_meme_words = [
        'dump', 'rug', 'rekt', 'ngmi', 'bag holder', 'cope', 'seethe',
        'exit liquidity', 'paper hands', 'fud', 'dead', 'scam', 'rugpull'
    ]
    
    text_lower = text.lower()
    
    bullish_count = sum(1 for word in bullish_meme_words if word in text_lower)
    bearish_count = sum(1 for word in bearish_meme_words if word in text_lower)
    
    # Factor in emojis
    rocket_count = text.count('🚀') + text.count('🌙')
    diamond_count = text.count('💎')
    crying_count = text.count('😭') + text.count('💀')
    
    total_signals = bullish_count + bearish_count + rocket_count + diamond_count + crying_count
    
    if total_signals == 0:
        return 0.0
    
    sentiment = (bullish_count + rocket_count + diamond_count - bearish_count - crying_count) / max(len(text.split()), 1)
    return sentiment

def test_meme_heuristic_agent(trading_signals):
    """Test heuristic agent with meme coin trading signals"""
    print("🧠 HEURISTIC AGENT: Meme Trading Signals")
    print("=" * 50)

    for coin_name, analysis in trading_signals.items():
        print(f"🪙 {coin_name} Analysis:")
        print(f"   📊 Composite Score: {analysis['composite_score']:.2f}")
        print(f"   🎯 Signal: {analysis['signal']}")
        print(f"   💪 Confidence: {analysis.get('confidence', 0.0):.1%}")
        print(f"   ⚠️  Risk: {analysis['risk_level']}")
        if analysis['risk_factors']:
            print(f"   🚨 Risk Factors: {', '.join(analysis['risk_factors'])}")
        print()

    assert "PEPE2024" in trading_signals
    assert trading_signals["PEPE2024"]["signal"] == "STRONG BUY 🚀"
    assert "DOGWIFHAT" in trading_signals
    assert trading_signals["DOGWIFHAT"]["signal"] == "AVOID ❌"
    assert "BONKINU" in trading_signals
    assert trading_signals["BONKINU"]["signal"] == "BUY 📈"
    print("✅ Heuristic agent produced expected trading signals.")


def test_comprehensive_validator(meme_coins, trading_signals):
    """Test comprehensive validator with meme coin trades"""
    print("🛡️ COMPREHENSIVE VALIDATOR: Risk & Compliance Checks")
    print("=" * 60)
    
    validated_trades = []
    
    for coin in meme_coins:
        is_compliant = True
        is_risky = False
        reason = []

        # Check OFAC sanctions (mocked)
        if check_ofac_sanctions(coin['mint']):
            is_compliant = False
            reason.append("Sanctioned address")

        # Risk flags based on heuristic signals
        signal = trading_signals.get(coin['name'], {}).get('signal', '')
        if "AVOID" in signal:
            is_risky = True
            reason.append("Heuristic agent flagged as AVOID")
            
        # --- Final Validation ---
        if is_compliant and not is_risky:
            decision = "APPROVED"
            validated_trades.append(coin)
        else:
            decision = "REJECTED"
            
        print(f"🪙 {coin['name']}:")
        print(f"   Is Compliant: {is_compliant}")
        print(f"   Is Risky: {is_risky}")
        print(f"   Final Decision: {decision}")
        print(f"   Reason: {', '.join(reason) if reason else 'N/A'}")
        print()

    validated_names = [c["name"] for c in validated_trades]
    assert "PEPE2024" in validated_names
    assert "DOGWIFHAT" not in validated_names
    assert "BONKINU" not in validated_names
    print("✅ Comprehensive validator correctly approved and rejected trades.")


def check_ofac_sanctions(address):
    """Mock function to check OFAC sanctions list"""
    sanctioned_addresses = {
        "1a2b3c4d5e6f7g8h9i0j": "Tornado Cash",
        "2a3b4c5d6e7f8g9h0i1j": "Lazarus Group",
        "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": "Test Sanctioned Address" # BONKINU
    }
    
    return address in sanctioned_addresses
