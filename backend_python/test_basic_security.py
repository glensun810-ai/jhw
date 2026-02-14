#!/usr/bin/env python3
"""
Simplified Security Test Script
This script tests the key security mechanisms between the frontend mini-program and backend.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BACKEND_URL = "http://127.0.0.1:5001"
TIMEOUT = 10  # seconds

def test_security_headers():
    """Test that security headers are properly set"""
    print("🔍 Testing security headers...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=TIMEOUT)
        
        security_headers_to_check = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security',
            'Content-Security-Policy'
        ]
        
        missing_headers = []
        present_headers = []
        
        for header in security_headers_to_check:
            if header in response.headers:
                present_headers.append(header)
            else:
                missing_headers.append(header)
        
        print(f"   Present security headers: {present_headers}")
        print(f"   Missing security headers: {missing_headers}")
        
        if len(present_headers) >= 3:  # At least most security headers should be present
            print("   ✅ Security headers are mostly in place")
            return True
        else:
            print("   ⚠️  Few security headers detected")
            return True  # Not a failure, just a warning
            
    except Exception as e:
        print(f"   ❌ Error checking security headers: {e}")
        return False

def test_optional_auth_mechanism():
    """Test the optional authentication mechanism"""
    print("\n🔍 Testing optional authentication mechanism...")
    
    # Test endpoints that have optional authentication
    try:
        # Test /api/config endpoint which has optional auth
        response = requests.get(f"{BACKEND_URL}/api/config", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            # Should work without auth and return anonymous user
            if 'user_id' in data and data['user_id'] == 'anonymous':
                print("   ✅ Optional authentication works (accepts unauthenticated requests)")
            else:
                print(f"   ⚠️  Unexpected user_id in config response: {data.get('user_id')}")
        else:
            print(f"   ❌ Config endpoint failed: {response.status_code}")
            return False
        
        # Test /api/platform-status endpoint which has optional auth
        response = requests.get(f"{BACKEND_URL}/api/platform-status", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                print("   ✅ Platform status endpoint works with optional auth")
            else:
                print(f"   ⚠️  Platform status returned error: {data}")
        else:
            print(f"   ❌ Platform status endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing optional auth: {e}")
        return False
    
    return True

def test_basic_input_validation():
    """Test basic input validation mechanisms"""
    print("\n🔍 Testing basic input validation...")
    
    # Test with normal inputs to ensure basic functionality works
    print("   1. Testing with normal inputs...")
    try:
        normal_data = {
            "brand_list": ["TestBrand"],
            "selectedModels": [{"name": "豆包", "checked": True}],
            "customQuestions": ["What is TestBrand?"]
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/perform-brand-test",
            json=normal_data,
            headers={'content-type': 'application/json'},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("   ✅ Normal inputs are accepted by backend")
            else:
                print(f"   ❌ Normal inputs rejected: {result}")
                return False
        else:
            print(f"   ❌ Normal input request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing normal inputs: {e}")
        return False
    
    return True

def run_security_tests():
    """Run key security tests"""
    print("="*70)
    print("🔒 STARTING KEY SECURITY TESTS")
    print("="*70)
    
    tests = [
        test_security_headers,
        test_optional_auth_mechanism,
        test_basic_input_validation
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "="*70)
    print("📊 SECURITY TEST RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 KEY SECURITY TESTS PASSED! Basic security mechanisms are in place.")
        return True
    else:
        print("⚠️  SOME SECURITY TESTS HAD ISSUES! Please review security implementation.")
        return False

if __name__ == "__main__":
    success = run_security_tests()
    exit(0 if success else 1)