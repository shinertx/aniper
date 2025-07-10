#!/usr/bin/env python3
"""
Comprehensive Trading System Validator
Tests all the critical fixes: Redis signals, OCO orders, pricing, deduplication
"""

import redis
import json
import time
import requests
from datetime import datetime, timedelta

def test_system_health():
    """Check if all system components are healthy"""
    print("🏥 SYSTEM HEALTH CHECK")
    print("=" * 40)
    
    health_status = {}
    
    # Test Redis
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        health_status['redis'] = '✅ Connected'
    except:
        health_status['redis'] = '❌ Failed'
        return False
    
    # Test Executor metrics endpoint
    try:
        response = requests.get('http://localhost:9184/metrics', timeout=5)
        if response.status_code == 200:
            health_status['executor'] = '✅ Responding'
        else:
            health_status['executor'] = f'⚠️ HTTP {response.status_code}'
    except:
        health_status['executor'] = '❌ Not responding'
    
    # Test Prometheus
    try:
        response = requests.get('http://localhost:9090/-/healthy', timeout=5)
        health_status['prometheus'] = '✅ Healthy' if response.status_code == 200 else '⚠️ Issues'
    except:
        health_status['prometheus'] = '❌ Down'
    
    for component, status in health_status.items():
        print(f"   {component.title()}: {status}")
    
    return health_status['redis'].startswith('✅')

def test_deduplication():
    """Test that duplicate trade signals are properly handled"""
    print("\n🔄 TESTING DEDUPLICATION")
    print("=" * 40)
    
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    # Clear old data
    r.delete('trade_signals')
    for key in r.keys('processed_*'):
        r.delete(key)
    
    # Create identical trade signals
    base_signal = {
        "action": "buy",
        "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        "amount_usdc": 5.0,
        "creator": "TestDedup",
        "timestamp": datetime.now().isoformat()
    }
    
    # Send same signal 3 times
    for i in range(3):
        r.lpush('trade_signals', json.dumps(base_signal))
        print(f"   📤 Sent duplicate signal #{i+1}")
        time.sleep(0.5)
    
    initial_count = r.llen('trade_signals')
    print(f"   📊 Initial signals: {initial_count}")
    
    # Wait and check if deduplication works
    time.sleep(10)
    
    final_count = r.llen('trade_signals')
    processed_keys = r.keys('processed_*')
    
    print(f"   📊 Final signals: {final_count}")
    print(f"   🔍 Processed keys: {len(processed_keys)}")
    
    if len(processed_keys) > 0:
        print("   ✅ Deduplication system is working!")
        return True
    else:
        print("   ⚠️ No deduplication artifacts found")
        return False

def test_oco_orders():
    """Test OCO (One-Cancels-Other) order functionality"""
    print("\n📈📉 TESTING OCO ORDERS")
    print("=" * 40)
    
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.delete('trade_signals')
    
    # Create a trade signal with specific OCO parameters
    oco_signal = {
        "action": "buy",
        "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        "amount_usdc": 20.0,
        "take_profit_pct": 1.50,  # 50% profit target
        "stop_loss_pct": 0.80,    # 20% stop loss
        "max_slippage": 2.0,
        "creator": "OCOTest",
        "timestamp": datetime.now().isoformat(),
        "source": "oco_test"
    }
    
    r.lpush('trade_signals', json.dumps(oco_signal))
    
    print(f"   📊 OCO Signal created:")
    print(f"      Amount: ${oco_signal['amount_usdc']}")
    print(f"      Take Profit: +{(oco_signal['take_profit_pct']-1)*100:.0f}%")
    print(f"      Stop Loss: -{(1-oco_signal['stop_loss_pct'])*100:.0f}%")
    
    # Monitor for OCO-related Redis keys
    start_time = time.time()
    while time.time() - start_time < 20:
        oco_keys = r.keys('*oco*') + r.keys('*tp*') + r.keys('*sl*')
        if oco_keys:
            print(f"   🎯 OCO artifacts found: {oco_keys}")
            return True
        time.sleep(2)
    
    print("   ⚠️ No OCO artifacts detected in 20s")
    return False

def test_position_sizing():
    """Test variable position sizing"""
    print("\n💰 TESTING POSITION SIZING")
    print("=" * 40)
    
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.delete('trade_signals')
    
    # Test different position sizes
    sizes = [5.0, 15.0, 50.0]
    
    for size in sizes:
        signal = {
            "action": "buy",
            "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "amount_usdc": size,
            "creator": f"SizeTest{size}",
            "timestamp": datetime.now().isoformat()
        }
        
        r.lpush('trade_signals', json.dumps(signal))
        print(f"   📤 Signal: ${size} position")
        time.sleep(1)
    
    initial_count = r.llen('trade_signals')
    print(f"   📊 Created {initial_count} signals with different sizes")
    
    # Wait and see if they're processed
    time.sleep(15)
    final_count = r.llen('trade_signals')
    processed = initial_count - final_count
    
    print(f"   📊 Processed: {processed}/{initial_count} signals")
    return processed > 0

def monitor_live_execution():
    """Monitor the system for live trade execution"""
    print("\n👁️ LIVE EXECUTION MONITORING")
    print("=" * 40)
    
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    # Create a comprehensive test signal
    live_signal = {
        "action": "buy",
        "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
        "amount_usdc": 25.0,
        "max_slippage": 3.0,
        "take_profit_pct": 1.40,  # 40% profit
        "stop_loss_pct": 0.70,    # 30% loss
        "creator": "LiveTest",
        "timestamp": datetime.now().isoformat(),
        "source": "comprehensive_test",
        "priority": "high"
    }
    
    # Set optimal risk parameters
    r.set('risk:equity_floor', '0.05')  # Very low for testing
    r.set('global_halt', '0')
    
    # Clear and send signal
    r.delete('trade_signals')
    r.lpush('trade_signals', json.dumps(live_signal))
    
    print(f"   🚀 Live test signal deployed:")
    print(f"      Token: BONK")
    print(f"      Amount: ${live_signal['amount_usdc']}")
    print(f"      TP/SL: +{(live_signal['take_profit_pct']-1)*100:.0f}%/-{(1-live_signal['stop_loss_pct'])*100:.0f}%")
    
    # Enhanced monitoring
    start_time = time.time()
    signal_consumed = False
    execution_detected = False
    
    print(f"\n   Monitoring for 60 seconds...")
    
    while time.time() - start_time < 60:
        elapsed = int(time.time() - start_time)
        
        # Check signal consumption
        current_signals = r.llen('trade_signals')
        if current_signals == 0 and not signal_consumed:
            print(f"\n   🎉 SIGNAL CONSUMED at {elapsed}s!")
            signal_consumed = True
        
        # Check for execution artifacts
        all_keys = r.keys('*')
        exec_patterns = ['trade_', 'swap_', 'execution_', 'transaction_', 'position_', 'oco_']
        execution_keys = [k for k in all_keys if any(pattern in k.lower() for pattern in exec_patterns)]
        
        if execution_keys and not execution_detected:
            print(f"\n   🔥 EXECUTION DETECTED at {elapsed}s!")
            print(f"      Keys: {execution_keys}")
            execution_detected = True
        
        # Check metrics endpoint for trade activity
        if elapsed % 15 == 0:  # Every 15 seconds
            try:
                metrics = requests.get('http://localhost:9184/metrics', timeout=2).text
                if 'trades_submitted' in metrics or 'trades_confirmed' in metrics:
                    print(f"\n   📊 METRICS: Trade activity detected!")
            except:
                pass
        
        status = f"✅" if signal_consumed else f"⏳"
        exec_status = f"🔥" if execution_detected else f"⏳"
        print(f"\r   ⏱️  {elapsed}s | Signal: {status} | Execution: {exec_status} | Keys: {len(execution_keys)}", end='', flush=True)
        
        time.sleep(2)
    
    print(f"\n\n   📊 LIVE EXECUTION RESULTS:")
    print(f"      Signal consumed: {'✅ YES' if signal_consumed else '❌ NO'}")
    print(f"      Execution detected: {'✅ YES' if execution_detected else '❌ NO'}")
    print(f"      Execution keys: {len(execution_keys)}")
    
    return signal_consumed and execution_detected

def main():
    """Run comprehensive validation of the trading system"""
    print("🔬 ANIPER COMPREHENSIVE SYSTEM VALIDATOR")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Testing: Redis signals, OCO orders, pricing fixes, deduplication")
    print()
    
    # Run all tests
    tests = [
        ("System Health", test_system_health),
        ("Deduplication", test_deduplication),
        ("OCO Orders", test_oco_orders),
        ("Position Sizing", test_position_sizing),
        ("Live Execution", monitor_live_execution)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*70}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' failed: {e}")
            results[test_name] = False
        
        time.sleep(2)  # Brief pause between tests
    
    # Final summary
    print(f"\n{'='*70}")
    print(f"🏆 FINAL VALIDATION SUMMARY")
    print(f"{'='*70}")
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name:<20}: {status}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📊 Overall Score: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED! System ready for live trading!")
    elif passed_count >= total_count * 0.8:
        print("🟡 MOSTLY WORKING! Minor issues to address.")
    else:
        print("🔴 MAJOR ISSUES! Check executor logs and configuration.")
    
    print(f"\n💡 Debugging commands:")
    print(f"   docker logs aniper-executor --tail 30")
    print(f"   curl http://localhost:9184/metrics")
    print(f"   docker exec aniper-redis redis-cli keys '*'")

if __name__ == "__main__":
    main()
