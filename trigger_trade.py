#!/usr/bin/env python3
"""
Manual Trade Trigger
Creates a simple trade signal to test if the executor will actually execute trades.
"""

import json
import time
import redis
from datetime import datetime

def trigger_test_trade():
    """Create a minimal trade signal to test executor execution"""
    print("🎯 TRIGGERING TEST TRADE")
    print("=" * 50)
    
    # Connect to Redis
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Connected to Redis")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    
    # 1. Set up minimal risk parameters for testing
    print("\n📋 Setting up test risk parameters...")
    r.set('risk:equity_floor', '1')  # Minimal equity requirement
    r.set('risk:max_position_size', '10')  # Small position size in USDC
    r.set('risk:max_slippage', '5.0')  # 5% max slippage
    r.set('global_halt', '0')  # Make sure trading is enabled
    
    # 2. Create a simple WASM-like configuration (simulated)
    print("📦 Creating mock trading model...")
    mock_wasm_config = {
        "model_id": "test_meme_trader_v1",
        "strategy": "simple_buy",
        "target_token": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        "action": "buy",
        "amount_usdc": "5",  # Small test amount
        "max_slippage": "3.0",
        "timestamp": datetime.now().isoformat()
    }
    
    r.set('current_model', json.dumps(mock_wasm_config))
    
    # 3. Create a trade signal
    print("📊 Creating trade signal...")
    trade_signal = {
        "signal_type": "BUY",
        "token_mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        "token_symbol": "BONK",
        "confidence": 0.8,
        "amount_usdc": 5,
        "max_slippage_bps": 300,  # 3%
        "reason": "Manual test trade for meme coin system validation",
        "timestamp": datetime.now().isoformat(),
        "source": "manual_test"
    }
    
    # Push to different queues the executor might be watching
    r.lpush('trade_signals', json.dumps(trade_signal))
    r.lpush('agent_output', json.dumps(trade_signal))
    r.set('latest_signal', json.dumps(trade_signal))
    
    # 4. Create config update that might trigger execution
    print("⚙️ Creating configuration update...")
    config_update = {
        "update_type": "trade_signal",
        "enabled": True,
        "signal": trade_signal,
        "timestamp": datetime.now().isoformat()
    }
    
    r.lpush('config_updates', json.dumps(config_update))
    
    # 5. Check what we've created
    print("\n📊 Current Redis state:")
    keys = r.keys('*')
    for key in sorted(keys):
        try:
            # Try different Redis data types
            key_type = r.type(key)
            if key_type == 'string':
                value = r.get(key)
                if value and len(str(value)) > 100:
                    print(f"  {key} (string): {str(value)[:100]}...")
                else:
                    print(f"  {key} (string): {value}")
            elif key_type == 'list':
                length = r.llen(key)
                print(f"  {key} (list): {length} items")
                if length > 0:
                    latest = r.lindex(key, 0)
                    print(f"    Latest: {latest[:50] if latest else 'None'}...")
            else:
                print(f"  {key} ({key_type}): [complex type]")
        except Exception as e:
            print(f"  {key}: [error reading: {e}]")
    
    print("\n🎯 Test trade signal created!")
    print("💰 Target: Buy $5 worth of BONK")
    print("📈 Max Slippage: 3%") 
    print("🤖 Signal pushed to multiple Redis queues")
    
    return True

def monitor_execution():
    """Monitor for trade execution"""
    print("\n👁️ MONITORING FOR TRADE EXECUTION")
    print("=" * 50)
    
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    print("Watching for 60 seconds...")
    start_time = time.time()
    
    while time.time() - start_time < 60:
        # Check for any new keys that might indicate execution
        keys = r.keys('*')
        execution_keys = [k for k in keys if 'execution' in k.lower() or 'transaction' in k.lower() or 'trade' in k.lower()]
        
        if execution_keys:
            print(f"\n🔍 Found potential execution keys: {execution_keys}")
            for key in execution_keys:
                value = r.get(key)
                print(f"  {key}: {value}")
        
        # Check for list items being consumed
        signal_count = r.llen('trade_signals')
        output_count = r.llen('agent_output')
        config_count = r.llen('config_updates')
        
        print(f"\r⏱️  {int(time.time() - start_time)}s - Signals: {signal_count}, Outputs: {output_count}, Configs: {config_count}", end='', flush=True)
        
        time.sleep(2)
    
    print("\n\n📊 Final Redis state:")
    keys = r.keys('*')
    for key in sorted(keys):
        value = r.get(key)
        if key in ['trade_signals', 'agent_output', 'config_updates']:
            count = r.llen(key)
            print(f"  {key}: {count} items")
            if count > 0:
                latest = r.lindex(key, 0)
                print(f"    Latest: {latest[:100] if latest else 'None'}...")
        else:
            print(f"  {key}: {str(value)[:100] if value else 'None'}")

def main():
    """Run the test trade trigger"""
    print("🚀 ANIPER TRADE EXECUTION TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Goal: Trigger actual trade execution on Devnet")
    print()
    
    # Trigger the test trade
    if trigger_test_trade():
        # Monitor for execution
        monitor_execution()
    
    print("\n✅ Test completed!")
    print("💡 Check executor logs with: docker logs aniper-executor --tail 20")
    print("📊 Check Prometheus metrics at: http://localhost:9090")

if __name__ == "__main__":
    main()
