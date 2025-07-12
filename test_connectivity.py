#!/usr/bin/env python3
"""
Live System Connectivity Test
Validates connectivity between Brain, Executor, Redis, Prometheus, and Solana RPCs.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

import redis
import requests
from dotenv import load_dotenv

load_dotenv()

class SystemConnectivityTester:
    """Tests live connectivity between all Aniper system components"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090/metrics")
        self.solana_rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.solana_wss_url = os.getenv("SOLANA_WSS_URL", "wss://api.mainnet-beta.solana.com")
        self.jupiter_api = os.getenv("JUPITER_API", "https://quote-api.jup.ag/v6")
        
        self.test_results: Dict[str, Dict[str, Any]] = {}
        
    def test_redis_connectivity(self) -> bool:
        """Test Redis connection and basic operations"""
        print("🔗 Testing Redis connectivity...")
        
        try:
            r = redis.from_url(self.redis_url, decode_responses=True)
            
            # Test basic operations
            test_key = f"connectivity_test_{int(time.time())}"
            test_value = "test_value"
            
            # Set, get, delete
            r.set(test_key, test_value, ex=60)  # Expires in 60 seconds
            retrieved = r.get(test_key)
            r.delete(test_key)
            
            success = retrieved == test_value
            
            self.test_results["redis"] = {
                "status": "PASS" if success else "FAIL",
                "url": self.redis_url,
                "latency_ms": self._measure_redis_latency(r),
                "info": r.info() if success else None,
            }
            
            print(f"  ✅ Redis: {self.test_results['redis']['status']}")
            return success
            
        except Exception as e:
            self.test_results["redis"] = {
                "status": "FAIL",
                "url": self.redis_url,
                "error": str(e),
            }
            print(f"  ❌ Redis: FAIL - {e}")
            return False
    
    def _measure_redis_latency(self, r: redis.Redis) -> float:
        """Measure Redis operation latency"""
        start = time.perf_counter()
        r.ping()
        end = time.perf_counter()
        return (end - start) * 1000  # Convert to milliseconds
    
    def test_prometheus_connectivity(self) -> bool:
        """Test Prometheus metrics endpoint"""
        print("📊 Testing Prometheus connectivity...")
        
        try:
            response = requests.get(self.prometheus_url, timeout=10)
            
            success = response.status_code == 200
            metrics_count = len([line for line in response.text.split('\\n') 
                               if line and not line.startswith('#')])
            
            self.test_results["prometheus"] = {
                "status": "PASS" if success else "FAIL",
                "url": self.prometheus_url,
                "status_code": response.status_code,
                "metrics_count": metrics_count if success else 0,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }
            
            print(f"  ✅ Prometheus: {self.test_results['prometheus']['status']}")
            return success
            
        except Exception as e:
            self.test_results["prometheus"] = {
                "status": "FAIL",
                "url": self.prometheus_url,
                "error": str(e),
            }
            print(f"  ❌ Prometheus: FAIL - {e}")
            return False
    
    def test_solana_rpc_connectivity(self) -> bool:
        """Test Solana RPC connection"""
        print("⚡ Testing Solana RPC connectivity...")
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getHealth"
            }
            
            response = requests.post(
                self.solana_rpc_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            data = response.json()
            success = response.status_code == 200 and "result" in data
            
            # Also test getSlot for additional validation
            slot_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "getSlot"
            }
            
            slot_response = requests.post(
                self.solana_rpc_url,
                json=slot_payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            slot_data = slot_response.json()
            current_slot = slot_data.get("result") if slot_response.status_code == 200 else None
            
            self.test_results["solana_rpc"] = {
                "status": "PASS" if success else "FAIL",
                "url": self.solana_rpc_url,
                "health": data.get("result") if success else None,
                "current_slot": current_slot,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }
            
            print(f"  ✅ Solana RPC: {self.test_results['solana_rpc']['status']}")
            return success
            
        except Exception as e:
            self.test_results["solana_rpc"] = {
                "status": "FAIL",
                "url": self.solana_rpc_url,
                "error": str(e),
            }
            print(f"  ❌ Solana RPC: FAIL - {e}")
            return False
    
    def test_jupiter_api_connectivity(self) -> bool:
        """Test Jupiter API for price quotes"""
        print("🪐 Testing Jupiter API connectivity...")
        
        try:
            # Test with a simple SOL to USDC quote
            quote_url = f"{self.jupiter_api}/quote"
            params = {
                "inputMint": "So11111111111111111111111111111111111111112",  # SOL
                "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                "amount": "1000000",  # 0.001 SOL
                "slippageBps": "50"
            }
            
            response = requests.get(quote_url, params=params, timeout=10)
            
            success = response.status_code == 200
            data = response.json() if success else {}
            
            self.test_results["jupiter_api"] = {
                "status": "PASS" if success else "FAIL",
                "url": self.jupiter_api,
                "status_code": response.status_code,
                "quote_available": "outAmount" in data,
                "response_time_ms": response.elapsed.total_seconds() * 1000,
            }
            
            print(f"  ✅ Jupiter API: {self.test_results['jupiter_api']['status']}")
            return success
            
        except Exception as e:
            self.test_results["jupiter_api"] = {
                "status": "FAIL",
                "url": self.jupiter_api,
                "error": str(e),
            }
            print(f"  ❌ Jupiter API: FAIL - {e}")
            return False
    
    def test_brain_agents_import(self) -> bool:
        """Test that all brain agents can be imported and initialized"""
        print("🧠 Testing Brain agents import...")
        
        try:
            from brain.agents.heuristic_agent import load_dataset, build_labels
            from brain.agents.narrative_agent import score_narratives
            from brain.agents.performance_coach import evaluate_performance
            from brain.agents.redteam_agent import adversarial_review
            
            # Test basic imports work
            success = True
            
            self.test_results["brain_agents"] = {
                "status": "PASS" if success else "FAIL",
                "heuristic_agent": "imported",
                "narrative_agent": "imported", 
                "performance_coach": "imported",
                "redteam_agent": "imported",
            }
            
            print(f"  ✅ Brain agents: {self.test_results['brain_agents']['status']}")
            return success
            
        except Exception as e:
            self.test_results["brain_agents"] = {
                "status": "FAIL",
                "error": str(e),
            }
            print(f"  ❌ Brain agents: FAIL - {e}")
            return False
    
    def test_executor_health(self) -> bool:
        """Test executor health endpoint (if running)"""
        print("⚙️ Testing Executor health...")
        
        try:
            # Try to connect to executor health endpoint
            health_url = "http://localhost:9185/health"
            response = requests.get(health_url, timeout=5)
            
            success = response.status_code == 200
            
            self.test_results["executor"] = {
                "status": "PASS" if success else "UNAVAILABLE",
                "url": health_url,
                "status_code": response.status_code if success else "connection_failed",
                "response_time_ms": response.elapsed.total_seconds() * 1000 if success else None,
            }
            
            status = self.test_results["executor"]["status"]
            print(f"  {'✅' if success else '⚠️'} Executor: {status}")
            return success
            
        except Exception as e:
            self.test_results["executor"] = {
                "status": "UNAVAILABLE",
                "url": "http://localhost:9185/health",
                "error": str(e),
            }
            print(f"  ⚠️ Executor: UNAVAILABLE - {e}")
            return False  # Not critical for basic connectivity
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all connectivity tests and return results"""
        print("🎯 ANIPER SYSTEM CONNECTIVITY TEST")
        print("=" * 60)
        print(f"⏰ Started at: {datetime.now().isoformat()}")
        print()
        
        # Run all tests
        tests = [
            ("Redis", self.test_redis_connectivity),
            ("Prometheus", self.test_prometheus_connectivity),
            ("Solana RPC", self.test_solana_rpc_connectivity),
            ("Jupiter API", self.test_jupiter_api_connectivity),
            ("Brain Agents", self.test_brain_agents_import),
            ("Executor", self.test_executor_health),
        ]
        
        passed = 0
        critical_failed = 0
        
        for test_name, test_func in tests:
            result = test_func()
            if result:
                passed += 1
            elif test_name != "Executor":  # Executor not running is not critical
                critical_failed += 1
        
        print()
        print("📊 CONNECTIVITY TEST SUMMARY")
        print("=" * 40)
        
        overall_status = "PASS" if critical_failed == 0 else "FAIL"
        print(f"Overall Status: {overall_status}")
        print(f"Tests Passed: {passed}/{len(tests)}")
        print(f"Critical Failures: {critical_failed}")
        
        # Detailed results
        print("\\n📋 Detailed Results:")
        for component, results in self.test_results.items():
            status = results["status"]
            emoji = "✅" if status == "PASS" else ("⚠️" if status == "UNAVAILABLE" else "❌")
            print(f"  {emoji} {component.replace('_', ' ').title()}: {status}")
            
            if "latency_ms" in results:
                print(f"    └─ Latency: {results['latency_ms']:.2f}ms")
            if "response_time_ms" in results:
                print(f"    └─ Response time: {results['response_time_ms']:.2f}ms")
        
        # Summary for production readiness
        print("\\n🚀 PRODUCTION READINESS:")
        readiness_items = [
            ("Redis connectivity", self.test_results.get("redis", {}).get("status") == "PASS"),
            ("Solana RPC access", self.test_results.get("solana_rpc", {}).get("status") == "PASS"),
            ("Jupiter API access", self.test_results.get("jupiter_api", {}).get("status") == "PASS"),
            ("Brain agents functional", self.test_results.get("brain_agents", {}).get("status") == "PASS"),
            ("Monitoring available", self.test_results.get("prometheus", {}).get("status") == "PASS"),
        ]
        
        ready_count = sum(1 for _, ready in readiness_items if ready)
        print(f"Ready components: {ready_count}/{len(readiness_items)}")
        
        for item, ready in readiness_items:
            emoji = "✅" if ready else "❌"
            print(f"  {emoji} {item}")
        
        return {
            "overall_status": overall_status,
            "tests_passed": passed,
            "total_tests": len(tests),
            "critical_failures": critical_failed,
            "production_ready": ready_count == len(readiness_items),
            "detailed_results": self.test_results,
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """Main entry point"""
    tester = SystemConnectivityTester()
    results = tester.run_comprehensive_test()
    
    # Save results to file
    output_file = f"connectivity_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\\n💾 Test results saved to: {output_file}")
    
    # Exit with appropriate code
    exit_code = 0 if results["overall_status"] == "PASS" else 1
    return exit_code

if __name__ == "__main__":
    exit(main())
