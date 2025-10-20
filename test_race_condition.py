import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Make a single HTTP request
def make_request(url, request_id):
    try:
        response = requests.get(url, timeout=10)
        return {'id': request_id, 'success': response.status_code == 200}
    except requests.RequestException:
        return {'id': request_id, 'success': False}

# Make many concurrent requests to demonstrate race condition
def test_race_condition(url, num_requests=100):
    print(f"Making {num_requests} concurrent requests to: {url}")
    print("This will test the thread safety of the hit counter...")
    print("-" * 60)
    
    start_time = time.time()
    
    # Make concurrent requests
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(make_request, url, i+1) for i in range(num_requests)]
        results = [f.result() for f in futures]
    
    elapsed = time.time() - start_time
    successful = sum(1 for r in results if r['success'])
    
    print(f"Completed {successful}/{num_requests} requests in {elapsed:.3f}s")
    print("-" * 60)
    
    return successful

# Main demonstration function
def main():
    HOST = "localhost"
    PORT = 8080
    NUM_REQUESTS = 100
    
    print("=" * 60)
    print("RACE CONDITION DEMONSTRATION")
    print("=" * 60)
    print("\nThis test demonstrates race conditions in concurrent counter updates.")
    print("\nTest procedure:")
    print("  1. First test with UNSAFE counter (--unsafe-counter --race-demo)")
    print("  2. Then test with SAFE counter (default, with locks)")
    print("  3. Compare the results")
    
    print(f"\nConfiguration:")
    print(f"  - Number of requests: {NUM_REQUESTS}")
    print(f"  - Server: {HOST}:{PORT}")
    
    # We'll test with a specific file
    TEST_FILE = "www/index.html"
    
    print(f"  - Test file: /{TEST_FILE}")
    
    print("\n" + "=" * 60)
    print("PART 1: Testing with UNSAFE counter")
    print("=" * 60)
    print("\nMake sure server is running with:")
    print("  python server.py www --unsafe-counter --race-demo")
    
    input("\nPress Enter when server is ready...")
    
    url = f"http://{HOST}:{PORT}/{TEST_FILE}"
    
    print("\nResetting counter by restarting server...")
    input("Press Enter after restarting the server...")
    
    print(f"\nMaking {NUM_REQUESTS} concurrent requests...")
    successful_unsafe = test_race_condition(url, NUM_REQUESTS)
    
    print(f"\nNow check the directory listing at http://{HOST}:{PORT}/www/")
    print(f"Look at the 'Hits' counter for {TEST_FILE}")
    print(f"Expected: {NUM_REQUESTS}, but you'll likely see LESS due to race conditions!")
    
    input("\nPress Enter after noting the hit count...")
    
    print("\n" + "=" * 60)
    print("PART 2: Testing with SAFE counter (with locks)")
    print("=" * 60)
    print("\nMake sure server is running with:")
    print("  python server.py www --race-demo")
    print("  (or just: python server.py www)")
    
    input("\nPress Enter when server is ready (after restart)...")
    
    print(f"\nMaking {NUM_REQUESTS} concurrent requests...")
    successful_safe = test_race_condition(url, NUM_REQUESTS)
    
    print(f"\nNow check the directory listing at http://{HOST}:{PORT}/www/")
    print(f"Look at the 'Hits' counter for {TEST_FILE}")
    print(f"Expected: {NUM_REQUESTS}, and it should match exactly!")
    
    input("\nPress Enter after noting the hit count...")
    
    print("\n" + "=" * 60)
    print("RESULTS ANALYSIS")
    print("=" * 60)
    print("\nExpected results:")
    print(f"  - With UNSAFE counter: Hit count < {NUM_REQUESTS} (due to race condition)")
    print(f"  - With SAFE counter:   Hit count = {NUM_REQUESTS} (all updates counted)")
    
    print("\nWhat happens in a race condition?")
    print("  1. Thread A reads counter value (e.g., 10)")
    print("  2. Thread B reads counter value (still 10)")
    print("  3. Thread A increments and writes (counter = 11)")
    print("  4. Thread B increments and writes (counter = 11) ← Lost update!")
    print("  5. Result: Two requests but counter only increased by 1")
    
    print("\nHow locks prevent this:")
    print("  - Only one thread can read-modify-write at a time")
    print("  - Other threads must wait their turn")
    print("  - All updates are preserved")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. The server is running")
        print("  2. requests library is installed: pip install requests")
        print("  3. The test file exists in your www directory")
