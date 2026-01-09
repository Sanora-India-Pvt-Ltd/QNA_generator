"""
Quick server health check script
Run this to test if your API server is working
"""
import requests
import sys
import json

def test_endpoint(url, name, timeout=5):
    """Test a single endpoint"""
    try:
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        r = requests.get(url, timeout=timeout)
        print(f"   ✅ Status: {r.status_code}")
        if r.headers.get('content-type', '').startswith('application/json'):
            print(f"   Response: {json.dumps(r.json(), indent=2)}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"   ❌ Connection Error: Server not running or unreachable")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout: Server took too long to respond")
        return False
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {str(e)}")
        return False

def main():
    # Default to localhost, but allow custom URL
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print("=" * 60)
    print("🧪 API Server Health Check")
    print("=" * 60)
    print(f"Testing server at: {base_url}")
    print("=" * 60)
    
    results = []
    
    # Test 1: Health endpoint
    results.append(test_endpoint(f"{base_url}/health", "Health Check"))
    
    # Test 2: Root endpoint
    results.append(test_endpoint(f"{base_url}/", "Root Endpoint"))
    
    # Test 3: API docs
    results.append(test_endpoint(f"{base_url}/docs", "API Documentation"))
    
    # Test 4: OpenAPI schema
    results.append(test_endpoint(f"{base_url}/openapi.json", "OpenAPI Schema"))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed! Server is working correctly.")
    elif passed == 0:
        print("❌ All tests failed! Server is not responding.")
        print("\n💡 Troubleshooting:")
        print("   1. Check if server is running: python api_pg_mcq.py")
        print("   2. Check if port is correct (default: 8000)")
        print("   3. Check server logs for errors")
    else:
        print("⚠️  Some tests failed. Check individual results above.")
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)



