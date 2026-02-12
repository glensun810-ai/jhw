#!/usr/bin/env python3
"""
Frontend-Backend Integration Test Script
This script simulates the actual requests that the mini-program frontend would make to the backend,
testing the complete integration flow.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BACKEND_URL = "http://127.0.0.1:5002"
TIMEOUT = 30  # seconds for longer operations

def test_frontend_backend_connection():
    """Test the connection between frontend and backend"""
    print("🔍 Testing frontend-backend connection...")
    
    # Test 1: Check server status (simulating what index.js does)
    print("   1. Checking server connection...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/test", timeout=TIMEOUT)
        if response.status_code == 200:
            print("   ✅ Server connection successful")
        else:
            print(f"   ❌ Server connection failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Server connection error: {e}")
        return False
    
    # Test 2: Simulate brand test request (the main functionality)
    print("   2. Testing brand test functionality...")
    try:
        # Send a simple brand test request
        test_data = {
            "brand_list": ["测试品牌", "竞品A", "竞品B"],
            "selectedModels": [
                {"name": "豆包", "checked": True},
                {"name": "通义千问", "checked": True}
            ],
            "customQuestions": [
                "介绍一下{brandName}",
                "{brandName}的主要产品是什么"
            ]
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success' and 'executionId' in result:
                execution_id = result['executionId']
                print(f"   ✅ Brand test initiated successfully, execution ID: {execution_id}")
                
                # Test 3: Poll for progress (simulating what index.js does)
                print("   3. Testing progress polling...")
                max_attempts = 30  # Wait up to 30 seconds
                attempts = 0
                
                while attempts < max_attempts:
                    progress_response = requests.get(
                        f"{BACKEND_URL}/api/test-progress?executionId={execution_id}",
                        timeout=TIMEOUT
                    )
                    
                    if progress_response.status_code == 200:
                        progress_data = progress_response.json()
                        status = progress_data.get('status', 'unknown')
                        progress = progress_data.get('progress', 0)
                        
                        print(f"      Progress: {progress}%, Status: {status}")
                        
                        if status in ['completed', 'failed']:
                            print(f"      Final status: {status}")
                            if status == 'completed':
                                print("   ✅ Brand test completed successfully")
                            else:
                                print(f"   ⚠️  Brand test failed: {progress_data.get('error', 'Unknown error')}")
                            break
                    
                    attempts += 1
                    time.sleep(1)  # Wait 1 second between polls
                
                if attempts >= max_attempts:
                    print("      ⚠️  Reached maximum polling attempts")
                
                return True
            else:
                print(f"   ❌ Brand test initiation failed: {result}")
                return False
        else:
            print(f"   ❌ Brand test request failed with status {response.status_code}")
            print(f"      Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Brand test error: {e}")
        return False

def test_results_page_data_flow():
    """Test the data flow for results page"""
    print("\n🔍 Testing results page data flow...")
    
    # Test getting AI platforms (used by results page)
    print("   1. Testing AI platforms retrieval...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/ai-platforms", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Retrieved AI platforms: {len(data.get('domestic', []))} domestic, {len(data.get('overseas', []))} overseas")
        else:
            print(f"   ❌ Failed to retrieve AI platforms: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ AI platforms retrieval error: {e}")
        return False
    
    # Test getting platform status (used by results page)
    print("   2. Testing platform status retrieval...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/platform-status", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print(f"   ✅ Retrieved platform statuses for {len(data.get('platforms', {}))} platforms")
            else:
                print(f"   ❌ Platform status API returned error: {data}")
                return False
        else:
            print(f"   ❌ Failed to retrieve platform status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Platform status retrieval error: {e}")
        return False
    
    return True

def test_history_endpoints():
    """Test history-related endpoints"""
    print("\n🔍 Testing history endpoints...")
    
    # Test getting test history (with a mock user ID)
    print("   1. Testing test history retrieval...")
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/test-history?userOpenid=anonymous&limit=10&offset=0",
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Retrieved test history: {data.get('count', 0)} records")
        else:
            print(f"   ❌ Failed to retrieve test history: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Test history retrieval error: {e}")
        return False
    
    return True

def run_integration_tests():
    """Run all frontend-backend integration tests"""
    print("="*70)
    print("🔄 STARTING FRONTEND-BACKEND INTEGRATION TESTS")
    print("="*70)
    
    tests = [
        test_frontend_backend_connection,
        test_results_page_data_flow,
        test_history_endpoints
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
        time.sleep(1)  # Small delay between tests
    
    print("\n" + "="*70)
    print("📊 INTEGRATION TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL INTEGRATION TESTS PASSED! Frontend and backend are properly connected.")
        return True
    else:
        print("⚠️  SOME INTEGRATION TESTS FAILED! Please check the integration points.")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)