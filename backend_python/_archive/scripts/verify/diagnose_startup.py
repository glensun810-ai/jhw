import sys
import os
import logging

# Configure logging to capture everything
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_startup():
    print("=== STARTING DIAGNOSTIC TEST ===")
    
    try:
        # 1. Test Config Loading
        print("\n[1] Testing Config Loading...")
        from config import Config
        print(f"Config loaded. App ID: {Config.WECHAT_APP_ID}")
        
        # 2. Test Adapter Imports
        print("\n[2] Testing Adapter Imports...")
        try:
            from wechat_backend.ai_adapters.gemini_adapter import GeminiAdapter, HAS_GEMINI
            print(f"GeminiAdapter imported. HAS_GEMINI flag: {HAS_GEMINI}")
        except Exception as e:
            print(f"ERROR importing GeminiAdapter: {e}")
            return False

        # 3. Test Factory Registration
        print("\n[3] Testing Adapter Factory...")
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        registered = AIAdapterFactory._adapters.keys()
        print(f"Registered adapters: {[k.value if hasattr(k, 'value') else k for k in registered]}")
        
        if AIPlatformType.GEMINI in AIAdapterFactory._adapters:
            print("SUCCESS: Gemini adapter is registered in factory.")
        else:
            print("FAILURE: Gemini adapter is NOT registered.")
            
        # 4. Test App Initialization
        print("\n[4] Testing App Initialization...")
        from wechat_backend import app
        print("App object created successfully.")
        
        print("\n=== DIAGNOSTIC TEST PASSED ===")
        return True

    except Exception as e:
        print(f"\n=== DIAGNOSTIC TEST FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_startup()
