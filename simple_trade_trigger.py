#!/usr/bin/env python3
"""
Enhanced Trade Trigger - Updated for Redis-enabled executor
Tests the new Redis trade signal system with proper formatting and monitoring.
"""

import redis
import json
import time
from datetime import datetime

def main():
    """Test the updated Redis-enabled trading system"""
    print("🎯 ENHANCED ANIPER TRADE EXECUTION TEST")
    print("=" * 60)
    print(f"Testing: Redis trade signals + OCO orders + proper pricing")
    print()
    
    # Connect to Redis
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Connected to Redis")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return
    
    # Clear old signals
    r.delete('trade_signals')
    print("🧹 Cleared old trade signals")
    
    # 1. Set enhanced risk parameters for updated system
    print("\n📋 Configuring enhanced risk parameters...")
    risk_params = {
        'risk:equity_floor': '0.1',      # Low threshold for devnet testing
        'risk:max_position_size': '50',   # Allow larger test trades
        'risk:max_slippage': '5.0',      # 5% max slippage
        'global_halt': '0',              # Ensure trading enabled
        'risk:equity_poll_ms': '5000'    # Poll every 5 seconds
    }
    
    for key, value in risk_params.items():
        r.set(key, value)
        print(f"   {key}: {value}")
    
    # 2. Create enhanced trade signal with OCO parameters
    print("\n📊 Creating enhanced BONK trade signal...")
    trade_signal = {
        "action": "buy",
        "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        "amount_usdc": 15.0,            # $15 test trade
        "max_slippage": 2.5,            # 2.5% slippage tolerance
        "take_profit_pct": 1.30,        # 30% take profit target
        "stop_loss_pct": 0.75,          # 25% stop loss
        "timestamp": datetime.now().isoformat(),
        "source": "enhanced_test",
        "creator": "TestTrader",
        "priority": "high",
        "test_mode": True
    }
    
    # Push to the trade_signals queue that executor monitors
    r.lpush('trade_signals', json.dumps(trade_signal))
    
    print(f"✅ Enhanced trade signal created:")
    print(f"   🪙 Token: BONK")
    print(f"   💰 Amount: ${trade_signal['amount_usdc']}")
    print(f"   📈 Take Profit: +{(trade_signal['take_profit_pct']-1)*100:.1f}%")
    print(f"   📉 Stop Loss: -{(1-trade_signal['stop_loss_pct'])*100:.1f}%")
    print(f"   ⚠️  Max Slippage: {trade_signal['max_slippage']}%")
    
    # 3. Enhanced monitoring with execution tracking
    print(f"\n👁️ Enhanced monitoring (45 seconds)...")
    start_time = time.time()
    initial_count = r.llen('trade_signals')
    last_count = initial_count
    
    while time.time() - start_time < 45:
        elapsed = int(time.time() - start_time)
        current_count = r.llen('trade_signals')
        
        # Check if signal was consumed
        if current_count != last_count:
            print(f"\n🎉 SIGNAL STATUS CHANGED! {last_count} -> {current_count}")
            if current_count == 0:
                print("✅ Trade signal consumed by executor!")
            last_count = current_count
        
        # Check for new Redis keys indicating execution
        all_keys = r.keys('*')
        execution_keys = [k for k in all_keys if any(pattern in k.lower() for pattern in [
            'trade_result', 'execution', 'transaction', 'position', 'pnl', 'swap_', 'oco_'
        ])]
        
        status_indicators = []
        if execution_keys:
            status_indicators.append(f"Exec keys: {len(execution_keys)}")
            
        # Check for deduplication tracking
        dedup_keys = [k for k in all_keys if 'processed_' in k or 'dedup' in k]
        if dedup_keys:
            status_indicators.append(f"Dedup: {len(dedup_keys)}")
        
        status = f" | {' | '.join(status_indicators)}" if status_indicators else ""
        print(f"\r⏱️  {elapsed}s - Signals: {current_count}{status}", end='', flush=True)
        
        # Show execution details if found
        if execution_keys and elapsed % 10 == 0:  # Every 10 seconds
            print(f"\n🔍 Execution artifacts found:")
            for key in execution_keys[:3]:  # Show first 3
                try:
                    value = r.get(key)
                    if value:
                        print(f"   {key}: {value[:80]}...")
                except:
                    count = r.llen(key) if r.type(key) == 'list' else 'unknown'
                    print(f"   {key}: [{count} items]")
        
        time.sleep(2)
    
    # 4. Final status report
    print(f"\n\n📊 FINAL EXECUTION REPORT")
    print("=" * 50)
    
    final_signals = r.llen('trade_signals')
    print(f"Trade signals: {initial_count} -> {final_signals}")
    
    if final_signals < initial_count:
        print("✅ Signal was consumed - executor is processing Redis signals!")
    else:
        print("⚠️  Signal not consumed - check executor logs")
    
    # Show all Redis keys for debugging
    all_keys = sorted(r.keys('*'))
    print(f"\nAll Redis keys ({len(all_keys)}):")
    for key in all_keys:
        try:
            key_type = r.type(key)
            if key_type == 'list':
                count = r.llen(key)
                print(f"   {key} (list): {count} items")
                if count > 0 and count <= 3:
                    for i in range(count):
                        item = r.lindex(key, i)
                        print(f"     [{i}]: {item[:60]}...")
            elif key_type == 'string':
                value = r.get(key)
                print(f"   {key} (string): {value}")
            else:
                print(f"   {key} ({key_type}): [complex type]")
        except Exception as e:
            print(f"   {key}: [error: {e}]")
    
    print(f"\n💡 Next steps:")
    print(f"   📋 Check executor logs: docker logs aniper-executor --tail 20")
    print(f"   📊 Check metrics: curl http://localhost:9184/metrics")
    print(f"   🔍 Check health: curl http://localhost:9184/health")
    print(f"   💰 Check wallet: May need USDC funding for actual swaps")

if __name__ == "__main__":
    main()
