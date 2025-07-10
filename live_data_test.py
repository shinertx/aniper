#!/usr/bin/env python3
"""
Live Data Testing Script
Connects to real Twitter/X feeds and Solana data to validate agents in real-time.
"""

import asyncio
import json
import time
import requests
import websockets
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

# Environment setup
TWITTER_BEARER = os.getenv('TWITTER_BEARER')
SOLANA_WSS_URL = os.getenv('SOLANA_WSS_URL', 'wss://api.devnet.solana.com')
SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.devnet.solana.com')
JUPITER_API = os.getenv('JUPITER_API', 'https://quote-api.jup.ag/v6')

class LiveDataCollector:
    def __init__(self):
        self.twitter_data = []
        self.solana_data = []
        self.jupiter_data = []
        self.start_time = datetime.now()
        
    async def collect_twitter_data(self, keywords: List[str] = None):
        """Collect live Twitter/X data for specified keywords"""
        if not TWITTER_BEARER:
            print("❌ Twitter API key not configured")
            return
            
        keywords = keywords or ["solana", "SOL", "$SOL", "pump.fun", "memecoins"]
        
        headers = {
            'Authorization': f'Bearer {TWITTER_BEARER}',
            'Content-Type': 'application/json'
        }
        
        # Twitter API v2 search endpoint
        for keyword in keywords:
            try:
                url = f"https://api.twitter.com/2/tweets/search/recent"
                params = {
                    'query': f'{keyword} -is:retweet lang:en',
                    'tweet.fields': 'created_at,public_metrics,context_annotations',
                    'max_results': 10
                }
                
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        self.twitter_data.extend(data['data'])
                        print(f"✅ Collected {len(data['data'])} tweets for '{keyword}'")
                else:
                    print(f"❌ Twitter API error {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"❌ Twitter collection error: {e}")
                
        return self.twitter_data
    
    async def collect_solana_websocket_data(self, duration_minutes: int = 5):
        """Collect live Solana WebSocket data"""
        try:
            async with websockets.connect(SOLANA_WSS_URL) as websocket:
                # Subscribe to account changes for popular tokens
                subscription = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "accountSubscribe",
                    "params": [
                        "11111111111111111111111111111112",  # System Program
                        {"encoding": "base64", "commitment": "finalized"}
                    ]
                }
                
                await websocket.send(json.dumps(subscription))
                print(f"🔗 Connected to Solana WebSocket: {SOLANA_WSS_URL}")
                
                end_time = datetime.now() + timedelta(minutes=duration_minutes)
                
                while datetime.now() < end_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        self.solana_data.append({
                            'timestamp': datetime.now().isoformat(),
                            'data': data
                        })
                        
                        if len(self.solana_data) % 10 == 0:
                            print(f"📊 Collected {len(self.solana_data)} Solana events")
                            
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"❌ WebSocket error: {e}")
                        break
                        
        except Exception as e:
            print(f"❌ Failed to connect to Solana WebSocket: {e}")
            
        return self.solana_data
    
    def collect_jupiter_quotes(self, tokens: List[str] = None):
        """Collect live Jupiter price quotes"""
        tokens = tokens or [
            "So11111111111111111111111111111111111112",  # SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        ]
        
        for token in tokens:
            try:
                url = f"{JUPITER_API}/quote"
                params = {
                    'inputMint': token,
                    'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                    'amount': 1000000,  # 1 SOL in lamports
                    'slippageBps': 50
                }
                
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    quote_data = response.json()
                    self.jupiter_data.append({
                        'timestamp': datetime.now().isoformat(),
                        'token': token,
                        'quote': quote_data
                    })
                    print(f"💰 Jupiter quote collected for token {token[:8]}...")
                else:
                    print(f"❌ Jupiter API error: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Jupiter collection error: {e}")
                
        return self.jupiter_data
    
    def save_collected_data(self):
        """Save all collected data to files for analysis"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save Twitter data
        if self.twitter_data:
            with open(f'live_twitter_data_{timestamp}.json', 'w') as f:
                json.dump(self.twitter_data, f, indent=2)
            print(f"💾 Saved {len(self.twitter_data)} Twitter records")
        
        # Save Solana data
        if self.solana_data:
            with open(f'live_solana_data_{timestamp}.json', 'w') as f:
                json.dump(self.solana_data, f, indent=2)
            print(f"💾 Saved {len(self.solana_data)} Solana records")
        
        # Save Jupiter data
        if self.jupiter_data:
            with open(f'live_jupiter_data_{timestamp}.json', 'w') as f:
                json.dump(self.jupiter_data, f, indent=2)
            print(f"💾 Saved {len(self.jupiter_data)} Jupiter records")

class LiveAgentTester:
    def __init__(self, data_collector: LiveDataCollector):
        self.data_collector = data_collector
        
    def test_narrative_agent(self):
        """Test narrative agent with live Twitter data"""
        if not self.data_collector.twitter_data:
            print("❌ No Twitter data available for narrative testing")
            return
            
        print("\n🤖 Testing Narrative Agent with Live Data:")
        
        for tweet in self.data_collector.twitter_data[:5]:  # Test first 5 tweets
            text = tweet.get('text', '')
            metrics = tweet.get('public_metrics', {})
            
            # Simulate narrative scoring (normally done by the agent)
            score = self.calculate_sentiment_score(text)
            
            print(f"Tweet: {text[:100]}...")
            print(f"Sentiment Score: {score:.3f}")
            print(f"Engagement: {metrics.get('like_count', 0)} likes, {metrics.get('retweet_count', 0)} retweets")
            print("-" * 50)
            
    def calculate_sentiment_score(self, text: str) -> float:
        """Simple sentiment scoring (would be replaced by actual agent logic)"""
        positive_words = ['bullish', 'moon', 'pump', 'up', 'good', 'great', 'amazing']
        negative_words = ['bearish', 'dump', 'down', 'bad', 'crash', 'terrible']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Simple scoring formula
        return (positive_count - negative_count) / max(len(text.split()), 1)
    
    def test_heuristic_agent(self):
        """Test heuristic agent with live market data"""
        if not self.data_collector.jupiter_data:
            print("❌ No Jupiter data available for heuristic testing")
            return
            
        print("\n📊 Testing Heuristic Agent with Live Market Data:")
        
        prices = []
        for quote in self.data_collector.jupiter_data:
            if 'quote' in quote and 'outAmount' in quote['quote']:
                price = float(quote['quote']['outAmount']) / 1000000  # Convert to readable price
                prices.append(price)
                
        if len(prices) >= 2:
            price_change = (prices[-1] - prices[0]) / prices[0] * 100
            volatility = np.std(prices) / np.mean(prices) * 100
            
            print(f"Price Change: {price_change:.2f}%")
            print(f"Volatility: {volatility:.2f}%")
            print(f"Sample Count: {len(prices)}")
            
            # Simulate trading signal
            if price_change > 2:
                signal = "BUY"
            elif price_change < -2:
                signal = "SELL"
            else:
                signal = "HOLD"
                
            print(f"🎯 Generated Signal: {signal}")
        else:
            print("❌ Insufficient market data for analysis")

async def main():
    """Run live data testing"""
    print("🚀 Starting Live Data Collection and Agent Testing")
    print("=" * 60)
    
    collector = LiveDataCollector()
    
    # Collect live data concurrently
    tasks = [
        collector.collect_twitter_data(['solana', '$SOL', 'pump.fun']),
        collector.collect_solana_websocket_data(duration_minutes=2),  # Shorter duration for testing
    ]
    
    # Run data collection
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect Jupiter quotes
    collector.collect_jupiter_quotes()
    
    # Save all data
    collector.save_collected_data()
    
    # Test agents with live data
    tester = LiveAgentTester(collector)
    tester.test_narrative_agent()
    tester.test_heuristic_agent()
    
    print("\n✅ Live data testing completed!")
    print(f"📊 Total Data Collected:")
    print(f"  - Twitter: {len(collector.twitter_data)} tweets")
    print(f"  - Solana: {len(collector.solana_data)} events") 
    print(f"  - Jupiter: {len(collector.jupiter_data)} quotes")

if __name__ == "__main__":
    asyncio.run(main())
