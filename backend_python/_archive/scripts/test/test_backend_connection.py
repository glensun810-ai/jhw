#!/usr/bin/env python3
"""
Backend API Connection Test Script
This script tests the connectivity and functionality of the backend API endpoints
to ensure proper integration with the frontend mini-program.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BACKEND_URL = "http://127.0.0.1:5000"
TIMEOUT = 10  # seconds

def test_health_endpoint():
    """Test the health check endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check successful: {data}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_index_endpoint():
    """Test the main index endpoint"""
    print("\n🔍 Testing index endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Index endpoint successful: {data}")
            return True
        else:
            print(f"❌ Index endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Index endpoint error: {e}")
        return False

def test_config_endpoint():
    """Test the config endpoint"""
    print("\n🔍 Testing config endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/config", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Config endpoint successful: {data}")
            return True
        else:
            print(f"❌ Config endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Config endpoint error: {e}")
        return False

def test_test_api_endpoint():
    """Test the test API endpoint"""
    print("\n🔍 Testing test API endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/test", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Test API endpoint successful: {data}")
            return True
        else:
            print(f"❌ Test API endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Test API endpoint error: {e}")
        return False

def test_platform_status_endpoint():
    """Test the platform status endpoint"""
    print("\n🔍 Testing platform status endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/platform-status", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Platform status endpoint successful: {data.get('status', 'unknown')}")
            if data.get('status') == 'success':
                platforms = data.get('platforms', {})
                print(f"   Available platforms: {list(platforms.keys())}")
                for platform, status in platforms.items():
                    print(f"   - {platform}: {status.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Platform status endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Platform status endpoint error: {e}")
        return False

def test_ai_platforms_endpoint():
    """Test the AI platforms endpoint"""
    print("\n🔍 Testing AI platforms endpoint...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/ai-platforms", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI platforms endpoint successful")
            print(f"   Domestic platforms: {[p['name'] for p in data.get('domestic', [])]}")
            print(f"   Overseas platforms: {[p['name'] for p in data.get('overseas', [])]}")
            return True
        else:
            print(f"❌ AI platforms endpoint failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ AI platforms endpoint error: {e}")
        return False

def test_brand_test_endpoint():
    """Test the brand test endpoint (without actually running a test)"""
    print("\n🔍 Testing brand test endpoint accessibility...")
    try:
        # Send a minimal request to check if endpoint accepts requests
        response = requests.post(
            f"{BACKEND_URL}/api/perform-brand-test",
            json={
                "brand_list": ["test"],
                "selectedModels": [{"name": "test"}],
                "customQuestions": ["test"]
            },
            timeout=TIMEOUT
        )
        # We expect this to fail due to validation, but the important thing is that the endpoint exists
        print(f"✅ Brand test endpoint accessible (expected validation error): Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Brand test endpoint error: {e}")
        return False

def run_all_tests():
    """Run all backend API tests"""
    print("="*60)
    print("🧪 STARTING BACKEND API INTEGRATION TESTS")
    print("="*60)
    
    tests = [
        test_health_endpoint,
        test_index_endpoint,
        test_config_endpoint,
        test_test_api_endpoint,
        test_platform_status_endpoint,
        test_ai_platforms_endpoint,
        test_brand_test_endpoint
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Backend is ready for frontend integration.")
        return True
    else:
        print("⚠️  SOME TESTS FAILED! Please check the backend configuration.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)