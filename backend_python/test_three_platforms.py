#!/usr/bin/env python3
"""
Diagnostic script to test Qwen, Doubao, and Zhipu AI platforms
with detailed logging to identify issues
"""

import os
import sys
import time
import requests
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set API keys directly for testing
os.environ['QWEN_API_KEY'] = 'sk-5261a4dfdf964a5c9a6364128cc4c653'
os.environ['DOUBAO_API_KEY'] = '2a376e32-8877-4df8-9865-7eb3e99c9f92'
os.environ['ZHIPU_API_KEY'] = '504d64a0ad234557a79ad0dbcba3685c.ZVznXgPMIsnHbiNh'

from legacy_config import Config

TEST_PROMPT = "你好，请用一句话介绍你自己。"


def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_qwen_api():
    """Test Qwen (Alibaba DashScope) API"""
    print_separator("Testing Qwen API (Alibaba DashScope)")
    
    api_key = Config.QWEN_API_KEY
    print(f"API Key: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else 'N/A'}")
    print(f"API Key Length: {len(api_key)}")
    
    if not api_key or len(api_key) < 10:
        print("❌ ERROR: Qwen API key is empty or too short")
        return False
    
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen-max",
        "input": {
            "messages": [{"role": "user", "content": TEST_PROMPT}]
        },
        "parameters": {
            "temperature": 0.7,
        }
    }
    
    print(f"Endpoint: {url}")
    print(f"Request Payload: {json.dumps(payload, ensure_ascii=False)[:200]}...")
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        latency = time.time() - start_time
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Latency: {latency:.2f}s")
        print(f"Raw Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("output") and data["output"].get("text"):
                print(f"✅ SUCCESS: {data['output']['text'][:100]}")
                return True
            else:
                print(f"❌ ERROR: No output in response: {data}")
                return False
        elif response.status_code == 401:
            print("❌ ERROR: 401 Unauthorized - Invalid API key")
            return False
        elif response.status_code == 403:
            print("❌ ERROR: 403 Forbidden - API key may be expired or insufficient permissions")
            return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timeout (30s)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ ERROR: Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False


def test_doubao_api():
    """Test Doubao (ByteDance VolcEngine) API"""
    print_separator("Testing Doubao API (ByteDance VolcEngine)")
    
    api_key = Config.DOUBAO_API_KEY
    print(f"API Key: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else 'N/A'}")
    print(f"API Key Length: {len(api_key)}")
    
    if not api_key or len(api_key) < 10:
        print("❌ ERROR: Doubao API key is empty or too short")
        return False
    
    # Doubao uses VolcEngine endpoint - fixed URL, deployment ID in model parameter
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # 修复：使用部署点 ID 而不是通用模型名称
    model_id = os.getenv('DOUBAO_MODEL_ID', 'ep-20260212000000-gd5tq')
    payload = {
        "model": model_id,  # 使用部署点 ID
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    print(f"Endpoint: {url}")
    print(f"Model: {model_id}")
    print(f"Request Payload: {json.dumps(payload, ensure_ascii=False)[:200]}...")
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        latency = time.time() - start_time
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Latency: {latency:.2f}s")
        print(f"Raw Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("choices") and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                print(f"✅ SUCCESS: {content[:100]}")
                return True
            else:
                print(f"❌ ERROR: No choices in response: {data}")
                return False
        elif response.status_code == 401:
            print("❌ ERROR: 401 Unauthorized - Invalid API key")
            return False
        elif response.status_code == 403:
            print("❌ ERROR: 403 Forbidden - API key may be expired or insufficient permissions")
            return False
        elif response.status_code == 404:
            print("❌ ERROR: 404 Not Found - Check endpoint URL or API key")
            return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timeout (30s)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ ERROR: Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False


def test_zhipu_api():
    """Test Zhipu AI API"""
    print_separator("Testing Zhipu AI API")
    
    api_key = Config.ZHIPU_API_KEY
    print(f"API Key: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else 'N/A'}")
    print(f"API Key Length: {len(api_key)}")
    
    if not api_key or len(api_key) < 10:
        print("❌ ERROR: Zhipu API key is empty or too short")
        return False
    
    # Zhipu API endpoint
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "glm-4",
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    print(f"Endpoint: {url}")
    print(f"Model: glm-4")
    print(f"Request Payload: {json.dumps(payload, ensure_ascii=False)[:200]}...")
    
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        latency = time.time() - start_time
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Latency: {latency:.2f}s")
        print(f"Raw Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("choices") and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                print(f"✅ SUCCESS: {content[:100]}")
                return True
            else:
                print(f"❌ ERROR: No choices in response: {data}")
                return False
        elif response.status_code == 401:
            print("❌ ERROR: 401 Unauthorized - Invalid API key")
            return False
        elif response.status_code == 403:
            print("❌ ERROR: 403 Forbidden - API key may be expired or insufficient permissions")
            return False
        elif response.status_code == 404:
            print("❌ ERROR: 404 Not Found - Check endpoint URL")
            return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timeout (30s)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ ERROR: Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False


def main():
    print("=" * 60)
    print("  AI Platform Diagnostic Test")
    print("  Testing Qwen, Doubao, and Zhipu APIs")
    print("=" * 60)
    print(f"Test Prompt: {TEST_PROMPT}")
    
    results = {
        'Qwen': test_qwen_api(),
        'Doubao': test_doubao_api(),
        'Zhipu': test_zhipu_api()
    }
    
    print_separator("Summary")
    for platform, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {platform}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("  All platforms are working correctly!")
    else:
        failed = [p for p, s in results.items() if not s]
        print(f"  Failed platforms: {', '.join(failed)}")
        print("\n  Please check:")
        print("  1. API keys are valid and not expired")
        print("  2. API keys have sufficient quota/balance")
        print("  3. Network connectivity to API endpoints")
        print("  4. Endpoint URLs are correct")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
