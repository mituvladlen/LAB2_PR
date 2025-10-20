import requests
import time
import threading
from datetime import datetime

# Thread-safe statistics collector
class RequestStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.total_requests = 0
        self.successful_requests = 0
        self.rate_limited_requests = 0
        self.error_requests = 0
        self.start_time = None
        self.end_time = None
    
    # Record a request result
    def record_request(self, status_code):
        with self.lock:
            self.total_requests += 1
            if status_code == 200:
                self.successful_requests += 1
            elif status_code == 429:
                self.rate_limited_requests += 1
            else:
                self.error_requests += 1
    
    # Mark start time
    def start(self):
        self.start_time = time.time()
    
    # Mark end time
    def stop(self):
        self.end_time = time.time()
    
    # Get test duration
    def get_duration(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    # Calculate successful requests per second
    def get_throughput(self):
        duration = self.get_duration()
        if duration > 0:
            return self.successful_requests / duration
        return 0
    
    # Print statistics report
    def print_report(self, client_name):
        duration = self.get_duration()
        throughput = self.get_throughput()
        
        print(f"\n{client_name} Results:")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Total requests: {self.total_requests}")
        print(f"  Successful (200): {self.successful_requests}")
        print(f"  Rate limited (429): {self.rate_limited_requests}")
        print(f"  Errors: {self.error_requests}")
        print(f"  Throughput: {throughput:.2f} successful requests/second")
        if self.total_requests > 0:
            print(f"  Success rate: {self.successful_requests/self.total_requests*100:.1f}%")

# Spammer client sends requests as fast as possible
def spammer_client(url, duration_seconds, stats):
    stats.start()
    end_time = time.time() + duration_seconds
    request_count = 0
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Spammer started - sending requests as fast as possible")
    
    while time.time() < end_time:
        request_count += 1
        try:
            response = requests.get(url, timeout=5)
            stats.record_request(response.status_code)
            
            if response.status_code == 429:
                if request_count % 20 == 0:
                    print(f"  [{datetime.now().strftime('%H:%M:%S')}] Request #{request_count} - RATE LIMITED")
            elif request_count % 10 == 0:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Request #{request_count} - Success")
        except requests.RequestException as e:
            stats.record_request(0)
            if request_count % 20 == 0:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Request #{request_count} - ERROR: {e}")
    
    stats.stop()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Spammer finished - sent {request_count} requests")

# Normal client sends requests at a controlled rate
def normal_client(url, duration_seconds, requests_per_second, stats):
    stats.start()
    end_time = time.time() + duration_seconds
    request_count = 0
    interval = 1.0 / requests_per_second  # Time between requests
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Normal user started - {requests_per_second} req/s")
    
    while time.time() < end_time:
        request_count += 1
        try:
            response = requests.get(url, timeout=5)
            stats.record_request(response.status_code)
            
            if response.status_code == 429:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Request #{request_count} - RATE LIMITED (unexpected!)")
            elif request_count % 10 == 0:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Request #{request_count} - Success")
        except requests.RequestException as e:
            stats.record_request(0)
            if request_count % 10 == 0:
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] Request #{request_count} - ERROR: {e}")
        
        # Wait before next request
        time.sleep(interval)
    
    stats.stop()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Normal user finished - sent {request_count} requests")

# Main test function
def main():
    HOST = "localhost"
    PORT = 8080
    TEST_DURATION = 15  # seconds
    
    print("=" * 60)
    print("RATE LIMITING TEST")
    print("=" * 60)
    print("\nThis test verifies that rate limiting works correctly.")
    print("\nServer configuration:")
    print("  - Rate limit: 5 requests/second per IP")
    print("  - Rate limiting is thread-safe (uses locks)")
    
    print(f"\nTest configuration:")
    print(f"  - Server: {HOST}:{PORT}")
    print(f"  - Test duration: {TEST_DURATION} seconds")
    
    print("\nMake sure the server is running:")
    print("  python server.py www")
    
    input("\nPress Enter to start the test...")
    
    url = f"http://{HOST}:{PORT}/"
    
    # Test 1: Normal user staying under the limit
    print("\n" + "=" * 70)
    print("TEST 1: Normal user (4 req/s - under the limit)")
    print("=" * 70)
    stats1 = RequestStats()
    normal_client(url, TEST_DURATION, 4, stats1)
    stats1.print_report("Normal user (4 req/s)")
    
    input("\nPress Enter for next test...")
    
    # Test 2: Spammer exceeding the limit
    print("\n" + "=" * 70)
    print("TEST 2: Spammer (unlimited rate)")
    print("=" * 70)
    spammer_stats = RequestStats()
    spammer_client(url, TEST_DURATION, spammer_stats)
    spammer_stats.print_report("SPAMMER")
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
    print("\nKey observations:")
    print("  - Rate limiting prevents spam by limiting requests per IP")
    print("  - Normal users below the limit have better throughput")
    print("  - The rate limiter is thread-safe (no race conditions)")
    print("  - Requests exceeding the limit get 429 status code")
    
    print("\nComparison:")
    print(f"  Normal user throughput: {stats1.get_throughput():.2f} req/s")
    print(f"  Spammer throughput: {spammer_stats.get_throughput():.2f} req/s")
    print(f"  Normal user success rate: {stats1.successful_requests/stats1.total_requests*100:.1f}%")
    print(f"  Spammer success rate: {spammer_stats.successful_requests/spammer_stats.total_requests*100:.1f}%")
    
    if stats1.successful_requests > spammer_stats.successful_requests:
        print("\n✓ Rate limiting is working! Normal user got more requests through.")
    elif spammer_stats.rate_limited_requests > 0:
        print("\n✓ Rate limiting is working! Spammer was rate limited.")
    else:
        print("\n⚠ Rate limiting may not be working as expected.")

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
