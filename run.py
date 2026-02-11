import requests
import json

# Base URL for your backend server
BASE_URL = 'http://127.0.0.1:5001'

def test_backend_connection():
    """Test basic connection to the backend"""
    try:
        response = requests.get(f'{BASE_URL}/')
        if response.status_code == 200:
            print("✓ Backend connection successful!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"✗ Backend connection failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error connecting to backend: {e}")
        return False

def test_api_endpoints():
    """Test various API endpoints"""
    endpoints = [
        '/api/config',
        '/api/test',
        '/api/access_token'
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(f'{BASE_URL}{endpoint}')
            print(f"Testing {endpoint}: Status {response.status_code}")
            if response.status_code == 200:
                print(f"  Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"  Error: {response.text}")
        except Exception as e:
            print(f"✗ Error testing {endpoint}: {e}")

def test_login_endpoint():
    """Test the login endpoint (without actual code, just to check if it responds properly)"""
    try:
        response = requests.post(
            f'{BASE_URL}/api/login',
            json={'code': 'fake_code_for_test'},
            headers={'Content-Type': 'application/json'}
        )
        print(f"Testing /api/login: Status {response.status_code}")
        print(f"  Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"✗ Error testing login endpoint: {e}")

if __name__ == "__main__":
    print("Testing WeChat Mini Program Backend...")
    print("="*50)

    if test_backend_connection():
        print("\nTesting API endpoints...")
        test_api_endpoints()

        print("\nTesting login endpoint...")
        test_login_endpoint()

        print("\nAll tests completed!")
    else:
        print("Cannot connect to backend. Make sure it's running on http://127.0.0.1:5001")