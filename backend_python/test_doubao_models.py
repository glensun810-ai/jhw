#!/usr/bin/env python3
"""
Test Doubao API with different model names to find the correct endpoint
"""

import os
import sys
import time
import requests
import json

TEST_PROMPT = "你好，请用一句话介绍你自己。"

# Doubao API Key
API_KEY = '2a376e32-8877-4df8-9865-7eb3e99c9f92'

# Common Doubao model names/endpoints
MODELS_TO_TEST = [
    # Standard model names
    "doubao-lite",
    "doubao-pro", 
    "doubao-1-5-pro",
    "doubao-1-5-lite",
    "doubao-1-5",
    "doubao",
    
    # Deployment ID format (ep-xxxx)
    "ep-default-model",
    
    # Full endpoint formats
    "doubao-lite.volces.com",
    "doubao-pro.volces.com",
]

BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

def test_model(model_name: str):
    """Test a specific model name"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        start_time = time.time()
        response = requests.post(BASE_URL, headers=headers, json=payload, timeout=30)
        latency = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data.get("choices") and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return True, f"✅ SUCCESS ({latency:.2f}s): {content[:80]}"
            else:
                return False, f"❌ No choices in response"
        elif response.status_code == 404:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Not Found")
            return False, f"❌ 404: {error_msg[:80]}"
        elif response.status_code == 401:
            return False, f"❌ 401: Unauthorized - Invalid API key"
        elif response.status_code == 403:
            return False, f"❌ 403: Forbidden"
        else:
            return False, f"❌ HTTP {response.status_code}: {response.text[:80]}"
            
    except Exception as e:
        return False, f"❌ ERROR: {type(e).__name__}: {e}"


def main():
    print("=" * 70)
    print("  Testing Doubao API with different model names")
    print("=" * 70)
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-5:]}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test Prompt: {TEST_PROMPT}")
    print("=" * 70)
    
    results = {}
    for model in MODELS_TO_TEST:
        print(f"\nTesting model: {model}")
        success, message = test_model(model)
        print(f"  Result: {message}")
        results[model] = success
    
    print("\n" + "=" * 70)
    print("  Summary")
    print("=" * 70)
    
    passed = [m for m, s in results.items() if s]
    failed = [m for m, s in results.items() if not s]
    
    if passed:
        print(f"\n✅ Working models: {', '.join(passed)}")
    if failed:
        print(f"❌ Failed models: {', '.join(failed)}")
    
    # Also test with alternative endpoint format
    print("\n" + "=" * 70)
    print("  Testing alternative endpoint formats")
    print("=" * 70)
    
    # Some Doubao endpoints use subdomain format
    for model in ["doubao-lite", "doubao-pro"]:
        alt_url = f"https://{model}.ark.cn-beijing.volces.com/api/v3/chat/completions"
        print(f"\nTesting endpoint: {alt_url}")
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": TEST_PROMPT}],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        try:
            response = requests.post(alt_url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get("choices"):
                    print(f"  ✅ SUCCESS: {data['choices'][0]['message']['content'][:80]}")
                else:
                    print(f"  ❌ No choices in response")
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
