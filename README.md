# Lab 2: Concurrent HTTP Server

This lab extends Lab 1 by adding multithreading capabilities, a hit counter to demonstrate race conditions, and rate limiting functionality.

## Overview

The server now handles multiple connections concurrently using a thread-per-request model. It includes:
- **Multithreading**: Each request is handled in a separate thread
- **Hit Counter**: Tracks requests to each file, with both safe and unsafe modes to demonstrate race conditions
- **Rate Limiting**: Limits requests to 5 per second per client IP address
- **Thread Safety**: Uses locks to prevent race conditions in shared resources

## Contents of Directory

- **server.py** - Multithreaded HTTP server with counter and rate limiting
- **test_performance.py** - Tests single-threaded vs multi-threaded performance
- **test_race_condition.py** - Demonstrates race conditions in the counter
- **test_rate_limiting.py** - Tests rate limiting functionality
- **Dockerfile** - Docker image configuration with Python 3.12
- **compose.yaml** - Docker Compose configuration
- **www/** - Directory containing files to serve (HTML, PNG, PDF)
- **downloads/** - Directory for client downloads

## Server Features

### Multithreading
- Thread-per-request model
- Configurable: can run in single-threaded mode with `--single-threaded` flag
- Significantly faster for concurrent requests

### Hit Counter
- Tracks number of requests to each file
- Displayed in directory listings under "Hits" column
- Two modes:
  - **Safe mode** (default): Uses locks, prevents race conditions
  - **Unsafe mode** (`--unsafe-counter`): Demonstrates race conditions
- Optional delay (`--race-demo`) to make race conditions more visible

### Rate Limiting
- Limits clients to 5 requests per second per IP address
- Uses sliding window algorithm
- Thread-safe implementation with locks
- Returns HTTP 429 (Too Many Requests) when limit exceeded
- Includes "Retry-After" header

## Running the Server

### Local Execution

**Basic usage:**
```powershell
python server.py www
```

**With options:**
```powershell
# Single-threaded mode
python server.py www --single-threaded

# With delay for testing
python server.py www --delay 1

# Unsafe counter (to demonstrate race condition)
python server.py www --unsafe-counter --race-demo

# Combination
python server.py www --delay 0.5 --unsafe-counter
```

**Command-line flags:**
- `--single-threaded` - Run in single-threaded mode (sequential requests)
- `--delay SECONDS` - Add artificial delay to each request (for testing)
- `--unsafe-counter` - Use unsafe counter (no locks, demonstrates race conditions)
- `--race-demo` - Add small delay in counter increment (makes race conditions visible)

**Server will run on:** http://localhost:8080

### Docker Execution

**Build the image:**
```powershell
docker compose build
```

**Start the server:**
```powershell
docker compose up -d server
```

**View logs:**
```powershell
docker compose logs -f server
```

**Stop the server:**
```powershell
docker compose down
```

**Access the server:** http://localhost:8080

## Testing

Install dependencies first:
```powershell
pip install requests
```

### 1. Performance Testing

Tests single-threaded vs multi-threaded performance:

```powershell
python test_performance.py
```

This test:
- Makes 10 concurrent requests
- Compares response times
- Calculates throughput and speedup
- Demonstrates the benefits of multithreading

**Expected results:**
- Single-threaded: ~10 seconds (sequential)
- Multi-threaded: ~1 second (parallel)
- Speedup: ~10x

### 2. Race Condition Testing

Demonstrates race conditions in the counter:

```powershell
python test_race_condition.py
```

**Part 1 - Unsafe counter:**
1. Start server with: `python server.py www --unsafe-counter --race-demo`
2. Run the test
3. Check directory listing - hit count will be LESS than 100 (race condition!)

**Part 2 - Safe counter:**
1. Restart server with: `python server.py www`
2. Run the test again
3. Check directory listing - hit count will be exactly 100 (fixed!)

**What's happening:**
- Without locks, multiple threads read/modify/write the counter simultaneously
- This causes lost updates (race condition)
- With locks, only one thread can update at a time (thread-safe)

### 3. Rate Limiting Testing

Tests the rate limiting functionality:

```powershell
python test_rate_limiting.py
```

This test:
- **Normal user** (4 req/s): Should succeed, stays under the limit
- **Spammer** (unlimited rate): Should get HTTP 429 errors

**Expected results:**
- Normal user: All 200 requests successful
- Spammer: Only ~5 successful per second, rest get 429 errors

## Docker Compose

The `compose.yaml` file defines two services:

### server
- Runs the multithreaded HTTP server
- Port 8080
- Mounts www directory

### requesttest
- Used to run test scripts
- Connects to the server

**Running tests with Docker:**
```powershell
docker compose run --rm requesttest test_performance.py
docker compose run --rm requesttest test_race_condition.py
docker compose run --rm requesttest test_rate_limiting.py
```

## Implementation Details

### Threading Model
- Uses `threading.Thread` for each request
- Threads are created with `daemon=True`
- Main thread listens for new connections
- Each connection is handled in `handle_client()` function

### Counter Implementation
```python
# Global shared state
file_hit_counter = defaultdict(int)
counter_lock = threading.Lock()

# Thread-safe increment
def increment_counter(file_path):
    with counter_lock:
        file_hit_counter[file_path] += 1
```

### Rate Limiting Implementation
```python
# Track requests per IP
rate_limit_data = defaultdict(list)
rate_limit_lock = threading.Lock()
MAX_REQUESTS_PER_SECOND = 5

# Sliding window algorithm
def check_rate_limit(client_ip):
    now = time.time()
    with rate_limit_lock:
        # Remove old timestamps
        timestamps = [t for t in rate_limit_data[client_ip] 
                      if now - t < 1.0]
        rate_limit_data[client_ip] = timestamps
        
        # Check limit
        if len(timestamps) < MAX_REQUESTS_PER_SECOND:
            timestamps.append(now)
            return True
        return False
```

## Comparison: Single-threaded vs Multi-threaded

| Aspect | Single-threaded | Multi-threaded |
|--------|----------------|----------------|
| Request handling | Sequential | Concurrent |
| 10 requests with 1s delay | ~10 seconds | ~1 second |
| Throughput | Low | High |
| Complexity | Simple | More complex |
| Race conditions | No | Possible (need locks) |

## Key Learnings

### Race Conditions
- Occur when multiple threads access shared data simultaneously
- Can cause lost updates and incorrect results
- Solution: Use locks (`threading.Lock()`) to protect critical sections

### Thread Safety
- Rate limiting uses locks to prevent race conditions
- Counter uses locks in safe mode
- Each shared resource needs its own lock

### Rate Limiting
- Sliding window algorithm tracks recent requests
- Thread-safe implementation essential
- Per-IP tracking prevents one client from affecting others

## Notes

- The server uses port 8080 by default
- Rate limit is 5 requests per second per IP
- Hit counter is displayed in directory listings
- All test scripts use the `requests` library
- Docker setup matches production-like environment

## Troubleshooting

**Server won't start:**
- Check if port 8080 is already in use
- Try stopping with `docker compose down` first

**Tests fail:**
- Make sure server is running
- Install requests: `pip install requests`
- Check the correct port (8080)

**Race condition not visible:**
- Use `--race-demo` flag to add delay
- Increase number of concurrent requests
- Make sure using `--unsafe-counter` flag
