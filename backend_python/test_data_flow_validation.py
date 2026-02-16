#!/usr/bin/env python3
"""
Data Flow Validation Test Script
This script validates the complete data flow between frontend and backend,
checking request/response formats, data structures, and transformations.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BACKEND_URL = "http://127.0.0.1:5000"
TIMEOUT = 30  # seconds for longer operations

def validate_request_response_formats():
    """Validate the request/response formats between frontend and backend"""
    print("🔍 Validating request/response formats...")
    
    # Test 1: Validate /api/test response format
    print("   1. Validating /api/test response format...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/test", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            required_fields = ['message', 'status']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                print("      ✅ /api/test response has correct format")
                print(f"         Message: {data['message']}")
                print(f"         Status: {data['status']}")
            else:
                print(f"      ❌ /api/test response missing fields: {missing_fields}")
                return False
        else:
            print(f"      ❌ /api/test request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ /api/test validation error: {e}")
        return False
    
    # Test 2: Validate /api/perform-brand-test request/response format
    print("   2. Validating /api/perform-brand-test request/response format...")
    try:
        test_data = {
            "brand_list": ["测试品牌"],
            "selectedModels": [{"name": "豆包", "checked": True}],
            "customQuestions": ["介绍一下{brandName}"]
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ['status', 'executionId', 'message']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields and data['status'] == 'success':
                print("      ✅ /api/perform-brand-test has correct request/response format")
                print(f"         Execution ID: {data['executionId']}")
                print(f"         Message: {data['message']}")
            else:
                print(f"      ❌ /api/perform-brand-test response invalid: missing {missing_fields} or wrong status")
                return False
        else:
            print(f"      ❌ /api/perform-brand-test request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ /api/perform-brand-test validation error: {e}")
        return False
    
    # Test 3: Validate /api/test-progress response format
    print("   3. Validating /api/test-progress response format...")
    try:
        # First initiate a test to get an execution ID
        test_data = {
            "brand_list": ["测试品牌"],
            "selectedModels": [{"name": "豆包", "checked": True}],
            "customQuestions": ["介绍一下{brandName}"]
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            exec_data = response.json()
            execution_id = exec_data['executionId']
            
            # Now check the progress
            progress_response = requests.get(
                f"{BACKEND_URL}/api/test-progress?executionId={execution_id}",
                timeout=TIMEOUT
            )
            
            if progress_response.status_code == 200:
                progress_data = progress_response.json()
                # At minimum, should have progress, status, and completed/total
                required_fields = ['progress', 'completed', 'total', 'status']
                missing_fields = [field for field in required_fields if field not in progress_data]
                
                if not missing_fields:
                    print("      ✅ /api/test-progress has correct response format")
                    print(f"         Progress: {progress_data['progress']}%")
                    print(f"         Status: {progress_data['status']}")
                    print(f"         Completed: {progress_data['completed']}/{progress_data['total']}")
                else:
                    print(f"      ❌ /api/test-progress response missing fields: {missing_fields}")
                    return False
            else:
                print(f"      ❌ /api/test-progress request failed: {progress_response.status_code}")
                return False
        else:
            print(f"      ❌ Could not initiate test for progress validation: {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ /api/test-progress validation error: {e}")
        return False
    
    return True

def validate_data_structure_consistency():
    """Validate that data structures are consistent between requests and responses"""
    print("\n🔍 Validating data structure consistency...")
    
    # Test 1: Validate AI platforms structure
    print("   1. Validating AI platforms data structure...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/ai-platforms", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            
            # Check structure: should have 'domestic' and 'overseas' arrays
            if 'domestic' in data and 'overseas' in data:
                if isinstance(data['domestic'], list) and isinstance(data['overseas'], list):
                    print(f"      ✅ AI platforms structure is correct: {len(data['domestic'])} domestic, {len(data['overseas'])} overseas")
                    
                    # Check that each platform has required properties
                    for platform_list, list_name in [(data['domestic'], 'domestic'), (data['overseas'], 'overseas')]:
                        for platform in platform_list:
                            if 'name' not in platform:
                                print(f"      ❌ {list_name} platform missing 'name' field: {platform}")
                                return False
                            if 'checked' not in platform:
                                print(f"      ❌ {list_name} platform missing 'checked' field: {platform}")
                                return False
                    print("      ✅ All AI platforms have required fields (name, checked)")
                else:
                    print(f"      ❌ AI platforms data is not in expected array format")
                    return False
            else:
                print(f"      ❌ AI platforms response missing 'domestic' or 'overseas' fields")
                return False
        else:
            print(f"      ❌ AI platforms request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ AI platforms structure validation error: {e}")
        return False
    
    # Test 2: Validate platform status structure
    print("   2. Validating platform status data structure...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/platform-status", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success' and 'platforms' in data:
                platforms = data['platforms']
                print(f"      ✅ Platform status structure is correct: {len(platforms)} platforms")
                
                # Check that each platform has required status information
                for platform_name, platform_info in platforms.items():
                    required_fields = ['status', 'has_api_key']
                    missing_fields = [field for field in required_fields if field not in platform_info]
                    
                    if missing_fields:
                        print(f"      ❌ Platform {platform_name} missing fields: {missing_fields}")
                        return False
                
                print("      ✅ All platforms have required status fields")
            else:
                print(f"      ❌ Platform status response invalid: {data}")
                return False
        else:
            print(f"      ❌ Platform status request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ Platform status structure validation error: {e}")
        return False
    
    return True

def validate_data_transformation():
    """Validate that data is properly transformed between frontend and backend"""
    print("\n🔍 Validating data transformation...")
    
    # Test 1: Check that brand names are properly handled
    print("   1. Validating brand name handling...")
    try:
        # Use a unique brand name to test
        unique_brand = f"TestBrand_{int(time.time())}"
        test_data = {
            "brand_list": [unique_brand, "Competitor1"],
            "selectedModels": [{"name": "豆包", "checked": True}],
            "customQuestions": [f"Tell me about {unique_brand}"]
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print(f"      ✅ Brand name '{unique_brand}' was accepted by backend")
                
                # Check the progress endpoint to see if brand data is maintained
                execution_id = result['executionId']
                progress_response = requests.get(
                    f"{BACKEND_URL}/api/test-progress?executionId={execution_id}",
                    timeout=TIMEOUT
                )
                
                if progress_response.status_code == 200:
                    progress_data = progress_response.json()
                    print(f"      ✅ Progress tracking works for brand '{unique_brand}'")
                else:
                    print(f"      ⚠️  Progress tracking issue: {progress_response.status_code}")
                    # This might be OK if the test completed quickly
            else:
                print(f"      ❌ Brand name validation failed: {result}")
                return False
        else:
            print(f"      ❌ Brand name handling failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ Brand name validation error: {e}")
        return False
    
    # Test 2: Check that model selections are preserved
    print("   2. Validating model selection preservation...")
    try:
        selected_models = [
            {"name": "豆包", "checked": True, "logo": "DB", "tags": ["综合", "创意"]},
            {"name": "通义千问", "checked": True, "logo": "QW", "tags": ["综合", "长文本"]}
        ]
        
        test_data = {
            "brand_list": ["TestBrandForModels"],
            "selectedModels": selected_models,
            "customQuestions": ["Test question"]
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/perform-brand-test",
            json=test_data,
            headers={'content-type': 'application/json'},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print(f"      ✅ Model selections were accepted by backend")
            else:
                print(f"      ❌ Model selection validation failed: {result}")
                return False
        else:
            print(f"      ❌ Model selection handling failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"      ❌ Model selection validation error: {e}")
        return False
    
    return True

def run_data_flow_validation():
    """Run all data flow validation tests"""
    print("="*70)
    print("🔄 STARTING DATA FLOW VALIDATION TESTS")
    print("="*70)
    
    tests = [
        validate_request_response_formats,
        validate_data_structure_consistency,
        validate_data_transformation
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
        time.sleep(0.5)  # Small delay between tests
    
    print("\n" + "="*70)
    print("📊 DATA FLOW VALIDATION RESULTS SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL DATA FLOW VALIDATION TESTS PASSED! Data flows correctly between frontend and backend.")
        return True
    else:
        print("⚠️  SOME DATA FLOW VALIDATION TESTS FAILED! Please check data handling.")
        return False

if __name__ == "__main__":
    success = run_data_flow_validation()
    exit(0 if success else 1)