#!/usr/bin/env python3
"""
Diagnostic script to troubleshoot Doubao API 404 errors
"""
import os
import requests
from urllib.parse import urljoin

def check_environment_variables():
    """Check if required environment variables are set"""
    print("🔍 Checking environment variables...")
    
    doubao_api_key = os.getenv('DOUBAO_API_KEY')
    doubao_model_id = os.getenv('DOUBAO_MODEL_ID')
    
    print(f"   DOUBAO_API_KEY: {'SET' if doubao_api_key else 'NOT SET'}")
    print(f"   DOUBAO_MODEL_ID: {doubao_model_id or 'NOT SET'}")
    
    if not doubao_api_key:
        print("   ❌ DOUBAO_API_KEY is not set in environment variables")
        print("   💡 Solution: Add DOUBAO_API_KEY to your .env file")
        return False
    
    return True

def test_api_connectivity(api_key, model_id):
    """Test basic connectivity to the Doubao API"""
    print("\n🔍 Testing API connectivity...")
    
    # Use the same configuration as the adapter
    base_url = "https://ark.cn-beijing.volces.com"
    endpoint = "/api/v3/chat/completions"
    full_url = urljoin(base_url, endpoint.lstrip('/'))
    
    print(f"   Testing URL: {full_url}")
    print(f"   Model ID: {model_id}")
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Send a minimal test request
    payload = {
        "model": model_id or "Doubao-pro",
        "messages": [{"role": "user", "content": "test"}],
        "temperature": 0.7,
        "max_tokens": 10
    }
    
    try:
        response = requests.post(full_url, headers=headers, json=payload, timeout=10)
        print(f"   Response Status: {response.status_code}")
        
        if response.status_code == 404:
            print("   ❌ 404 Error: API endpoint not found")
            print("   💡 This suggests either:")
            print("      1. Incorrect API endpoint URL")
            print("      2. Invalid API key (some services return 404 instead of 401 for invalid keys)")
            print("      3. Service is not available at this endpoint")
            return False
        elif response.status_code == 401:
            print("   ❌ 401 Error: Invalid API key")
            print("   💡 Please check your DOUBAO_API_KEY")
            return False
        elif response.status_code == 429:
            print("   ⚠️  429 Error: Rate limit exceeded (but API is reachable)")
            return True
        elif response.status_code == 200:
            print("   ✅ 200 Success: API is working correctly")
            return True
        else:
            print(f"   ⚠️  Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Connection Error: Cannot reach the API server")
        print("   💡 Check your internet connection and firewall settings")
        return False
    except requests.exceptions.Timeout:
        print("   ⚠️  Timeout: Request took too long")
        print("   💡 The API server might be slow or unreachable")
        return False
    except Exception as e:
        print(f"   ❌ Request failed with error: {e}")
        return False

def suggest_api_configuration():
    """Provide suggestions for API configuration"""
    print("\n💡 API Configuration Suggestions:")
    print("   1. Verify your DOUBAO_API_KEY is correct")
    print("   2. Check if you need to activate the Doubao API service")
    print("   3. Confirm the correct endpoint URL with Doubao documentation")
    print("   4. Ensure your account has sufficient permissions and quota")
    print("   5. Check if there are any IP whitelist requirements")

def main():
    print("="*60)
    print("Doubao API 404 Error Diagnostic Tool")
    print("="*60)
    
    env_ok = check_environment_variables()
    
    if not env_ok:
        print("\n🚨 Environment variables are not properly configured!")
        print("   Please set DOUBAO_API_KEY in your .env file before proceeding.")
        suggest_api_configuration()
        return False
    
    # Get the API key and model ID from environment
    api_key = os.getenv('DOUBAO_API_KEY')
    model_id = os.getenv('DOUBAO_MODEL_ID', 'Doubao-pro')
    
    connectivity_ok = test_api_connectivity(api_key, model_id)
    
    if not connectivity_ok:
        print("\n🚨 API connectivity test failed!")
        suggest_api_configuration()
        return False
    
    print("\n✅ All diagnostics passed! The API should be working correctly.")
    return True

if __name__ == "__main__":
    main()