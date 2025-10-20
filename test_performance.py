import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Make a single HTTP request and measure time
def make_request(url, request_id):
    start = time.time()
    try:
        response = requests.get(url, timeout=30)
        elapsed = time.time() - start
        return {
            'id': request_id,
            'status': response.status_code,
            'time': elapsed,
            'success': True
        }
    except requests.RequestException as e:
        elapsed = time.time() - start
        return {
            'id': request_id,
            'status': 0,
            'time': elapsed,
            'success': False,
            'error': str(e)
        }

# Make multiple concurrent requests and measure total time
def test_concurrent_requests(url, num_requests=10):
    print(f"\nTesting with {num_requests} concurrent requests to {url}")
    print("-" * 60)
    
    start_time = time.time()
    
    # Use ThreadPoolExecutor to make concurrent requests
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(make_request, url, i+1) for i in range(num_requests)]
        
        results = []
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "✓" if result['success'] else "✗"
            print(f"  Request {result['id']:2d}: {status} [{result['time']:.3f}s]")
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    successful = sum(1 for r in results if r['success'])
    failed = num_requests - successful
    avg_time = sum(r['time'] for r in results) / len(results)
    
    print("-" * 60)
    print(f"Total time: {total_time:.3f}s")
    print(f"Average request time: {avg_time:.3f}s")
    print(f"Successful requests: {successful}/{num_requests}")
    print(f"Failed requests: {failed}")
    print(f"Throughput: {successful/total_time:.2f} requests/second")
    
    return {
        'total_time': total_time,
        'avg_request_time': avg_time,
        'successful': successful,
        'failed': failed,
        'throughput': successful/total_time
    }

# Main test function
def main():
    # Test configuration
    HOST = "localhost"
    PORT = 8080
    NUM_REQUESTS = 10
    
    # Test file path
    TEST_PATH = "/"
    
    print("=" * 60)
    print("HTTP Server Performance Comparison Test")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  - Number of concurrent requests: {NUM_REQUESTS}")
    print(f"  - Server: {HOST}:{PORT}")
    print(f"  - Test path: {TEST_PATH}")
    print("\nNote: Make sure the server is running with ~1s delay:")
    print("  Single-threaded: python server.py www --single-threaded --delay 1")
    print("  Multi-threaded:  python server.py www --delay 1")
    
    url = f"http://{HOST}:{PORT}{TEST_PATH}"
    
    input("\nPress Enter to start single-threaded test...")
    print("\n" + "=" * 60)
    print("TEST 1: SINGLE-THREADED SERVER")
    print("=" * 60)
    single_results = test_concurrent_requests(url, NUM_REQUESTS)
    
    input("\n\nPress Enter to start multi-threaded test (restart server in multi-threaded mode)...")
    print("\n" + "=" * 60)
    print("TEST 2: MULTI-THREADED SERVER")
    print("=" * 60)
    multi_results = test_concurrent_requests(url, NUM_REQUESTS)
    
    # Comparison
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"\nSingle-threaded:")
    print(f"  Total time: {single_results['total_time']:.3f}s")
    print(f"  Throughput: {single_results['throughput']:.2f} req/s")
    
    print(f"\nMulti-threaded:")
    print(f"  Total time: {multi_results['total_time']:.3f}s")
    print(f"  Throughput: {multi_results['throughput']:.2f} req/s")
    
    speedup = single_results['total_time'] / multi_results['total_time']
    print(f"\nSpeedup: {speedup:.2f}x")
    print(f"Time saved: {single_results['total_time'] - multi_results['total_time']:.3f}s")
    
    print("\n" + "=" * 60)
    print("Analysis:")
    print("-" * 60)
    print(f"With {NUM_REQUESTS} concurrent requests and ~1s delay per request:")
    print(f"  - Single-threaded server should take ~{NUM_REQUESTS}s (sequential)")
    print("  - Multi-threaded server should take ~1s (parallel)")
    print(f"  - Actual speedup: {speedup:.2f}x")
    
    if speedup > 5:
        print("\n Multi-threading is working effectively!")
    else:
        print("\n Multi-threading may not be working as expected.")

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
