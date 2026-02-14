import sys
import os

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Attempting to import app...")
    from wechat_backend import app
    print("SUCCESS: App imported successfully.")
    
    print("Attempting to create test client...")
    client = app.test_client()
    
    print("Testing /health endpoint...")
    response = client.get('/health')
    print(f"Health check status: {response.status_code}")
    print(f"Health check response: {response.json}")
    
    if response.status_code == 200:
        print("SUCCESS: Backend service started and is healthy.")
    else:
        print("FAILURE: Health check failed.")

except Exception as e:
    print(f"FAILURE: Startup failed with error: {e}")
    import traceback
    traceback.print_exc()
