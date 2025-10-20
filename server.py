import socket
import sys
import os
import mimetypes
import urllib.parse
import threading
import time
from collections import defaultdict
from datetime import datetime

# File types we allow to serve; other types return 404
ALLOWED_MIME = {"text/html", "image/png", "application/pdf"}

# Global counter for file access (with thread-safe option)
file_hit_counter = defaultdict(int)
counter_lock = threading.Lock()

# Rate limiting structures
rate_limit_data = defaultdict(list)  # IP -> list of request timestamps
rate_limit_lock = threading.Lock()
MAX_REQUESTS_PER_SECOND = 5

# Configuration flags
USE_THREAD_SAFE_COUNTER = True  # Set to False to demonstrate race conditions
SIMULATE_RACE_CONDITION = False  # Set to True to force race conditions

def build_response(status_code: int, reason: str, headers: dict, body: bytes) -> bytes:
    """Build a raw HTTP/1.1 response (status line + headers + body)."""
    lines = [f"HTTP/1.1 {status_code} {reason}"]
    for k, v in headers.items():
        lines.append(f"{k}: {v}")
    head = "\r\n".join(lines) + "\r\n\r\n"
    return head.encode() + (body or b"")

def not_found_response() -> bytes:
    """Return a minimal 404 Not Found HTML response with Content-Length."""
    body = b"<html><body><h1>404 Not Found</h1></body></html>"
    return build_response(404, "Not Found", {"Content-Type": "text/html", "Content-Length": str(len(body))}, body)

def rate_limited_response() -> bytes:
    """Return a 429 Too Many Requests response."""
    body = b"<html><body><h1>429 Too Many Requests</h1><p>Rate limit exceeded. Please slow down.</p></body></html>"
    return build_response(429, "Too Many Requests", {
        "Content-Type": "text/html",
        "Content-Length": str(len(body)),
        "Retry-After": "1"
    }, body)

def check_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded rate limit. Returns True if allowed, False if rate limited."""
    with rate_limit_lock:
        now = time.time()
        # Clean old timestamps (older than 1 second)
        rate_limit_data[client_ip] = [ts for ts in rate_limit_data[client_ip] if now - ts < 1.0]
        
        # Check if rate limit exceeded
        if len(rate_limit_data[client_ip]) >= MAX_REQUESTS_PER_SECOND:
            return False
        
        # Add current request timestamp
        rate_limit_data[client_ip].append(now)
        return True

def increment_counter(file_path: str):
    """Increment hit counter for a file. Can be thread-safe or not based on flag."""
    if USE_THREAD_SAFE_COUNTER:
        with counter_lock:
            if SIMULATE_RACE_CONDITION:
                # Add delay to force race condition even with lock (for demo purposes)
                current = file_hit_counter[file_path]
                time.sleep(0.001)  # Small delay
                file_hit_counter[file_path] = current + 1
            else:
                file_hit_counter[file_path] += 1
    else:
        # Naive implementation without lock - will have race conditions
        if SIMULATE_RACE_CONDITION:
            current = file_hit_counter[file_path]
            time.sleep(0.001)  # Small delay to increase chance of race condition
            file_hit_counter[file_path] = current + 1
        else:
            file_hit_counter[file_path] += 1

def get_hit_count(file_path: str) -> int:
    """Get hit counter for a file in a thread-safe way."""
    with counter_lock:
        return file_hit_counter[file_path]

def generate_directory_listing(root_dir: str, rel_path: str) -> bytes:
    """Generate an HTML directory listing for rel_path under root_dir with hit counters."""
    safe_rel = rel_path.strip("/")
    abs_dir = os.path.join(root_dir, safe_rel)
    try:
        names = os.listdir(abs_dir)
    except OSError:
        return not_found_response()

    # Custom ordering: index.html first, then doc.pdf, then image.png, then the rest
    priority = {"index.html": 0, "doc.pdf": 1, "image.png": 2}
    def sort_key(name: str):
        lname = name.lower()
        return (priority.get(lname, 10), lname)
    items = sorted(names, key=sort_key)

    title_path = "/" + (safe_rel + "/" if safe_rel else "")
    
    # Generate HTML with table for hit counter (matching Victoria's style)
    lines = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>Directory listing for " + title_path + "</title>",
        "<style>",
        "body{font-family:system-ui,Segoe UI,Arial; margin:20px}",
        "h1{font-size:2em; margin-bottom:20px}",
        "table{border-collapse:collapse; width:100%; max-width:800px}",
        "th,td{border:1px solid #000; padding:8px; text-align:left}",
        "th{background-color:#f0f0f0; font-weight:bold}",
        "a{color:#0000EE; text-decoration:underline}",
        "a:visited{color:#551A8B}",
        "</style>",
        "</head><body>",
        f"<h1>Directory listing for {title_path}</h1>",
        "<table>",
        "<tr><th>File / Directory</th><th>Hits</th></tr>",
    ]

    # Parent directory link if not root
    if safe_rel:
        parent = os.path.dirname(safe_rel)
        parent_href = "/" + (urllib.parse.quote(parent) + "/" if parent else "")
        lines.append(f"<tr><td><a href=\"{parent_href}\">Parent Directory</a></td><td>-</td></tr>")

    for name in items:
        item_rel = (safe_rel + "/" if safe_rel else "") + name
        item_abs = os.path.join(root_dir, item_rel)
        is_dir = os.path.isdir(item_abs)
        display = name + ("/" if is_dir else "")
        href = "/" + urllib.parse.quote(item_rel) + ("/" if is_dir else "")
        
        # Get hit count for this file (not directories)
        hit_count = get_hit_count(item_rel) if not is_dir else "-"
        
        lines.append(f"<tr><td><a href=\"{href}\">{display}</a></td><td>{hit_count}</td></tr>")
    
    lines += ["</table>", "</body></html>"]
    body = "\n".join(lines).encode("utf-8")
    return build_response(200, "OK", {"Content-Type": "text/html", "Content-Length": str(len(body))}, body)

def serve_path(client_socket, root_dir: str, raw_path: str, delay: float = 0):
    """Serve a file or directory listing for the requested path with optional delay."""
    # Add delay to simulate processing time (for testing)
    if delay > 0:
        time.sleep(delay)
    
    # Decode URL and normalize path
    unquoted = urllib.parse.unquote(raw_path)
    rel = unquoted.lstrip("/")

    root_real = os.path.realpath(root_dir)
    abs_path = os.path.realpath(os.path.join(root_real, rel))

    # Prevent directory traversal
    if not (abs_path == root_real or abs_path.startswith(root_real + os.sep)):
        client_socket.sendall(not_found_response())
        return

    # If path is a directory (or root), return listing
    if rel == "" or os.path.isdir(abs_path):
        response = generate_directory_listing(root_real, rel)
        client_socket.sendall(response)
        return

    # Increment counter for file access
    increment_counter(rel)

    # Serve file if exists and allowed
    if not os.path.exists(abs_path):
        client_socket.sendall(not_found_response())
        return

    mime_type, _ = mimetypes.guess_type(abs_path)
    if mime_type not in ALLOWED_MIME:
        client_socket.sendall(not_found_response())
        return

    with open(abs_path, "rb") as f:
        body = f.read()
    response = build_response(200, "OK", {"Content-Type": mime_type, "Content-Length": str(len(body))}, body)
    client_socket.sendall(response)

def handle_client(client_socket, addr, directory, delay=0):
    """Handle a client connection in a separate thread."""
    try:
        client_ip = addr[0]
        
        # Check rate limit
        if not check_rate_limit(client_ip):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Rate limited: {client_ip}")
            client_socket.sendall(rate_limited_response())
            return
        
        request = client_socket.recv(1024).decode(errors="ignore")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Request from {addr}: {request.split()[0:2] if request else 'empty'}")

        # Parse request
        try:
            path = request.split()[1]
        except IndexError:
            path = "/"

        serve_path(client_socket, directory, path, delay)
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        client_socket.close()

def run_server(directory, host="0.0.0.0", port=8080, use_threading=True, delay=0):
    """
    Run HTTP server.
    
    Args:
        directory: Root directory to serve
        host: Host to bind to
        port: Port to bind to
        use_threading: If True, use threading for concurrent requests
        delay: Artificial delay in seconds to simulate processing time
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(10)  # Increased backlog for concurrent connections
    
    mode = "multithreaded" if use_threading else "single-threaded"
    print(f"Serving {directory} on {host}:{port} ({mode} mode)")
    if delay > 0:
        print(f"Artificial delay: {delay}s per request")
    print(f"Rate limit: {MAX_REQUESTS_PER_SECOND} requests/second per IP")
    print(f"Counter mode: {'Thread-safe' if USE_THREAD_SAFE_COUNTER else 'Naive (race conditions possible)'}")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            
            if use_threading:
                # Handle request in a new thread
                thread = threading.Thread(target=handle_client, args=(client_socket, addr, directory, delay))
                thread.daemon = True
                thread.start()
            else:
                # Handle request in main thread (blocking)
                handle_client(client_socket, addr, directory, delay)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python server.py <directory> [--single-threaded] [--delay SECONDS] [--unsafe-counter] [--race-demo]")
        print("\nOptions:")
        print("  --single-threaded    Run in single-threaded mode (default: multi-threaded)")
        print("  --delay SECONDS      Add artificial delay to simulate work (default: 0)")
        print("  --unsafe-counter     Use naive counter without locks (for race condition demo)")
        print("  --race-demo          Add delays to force race conditions (for demonstration)")
        sys.exit(1)
    
    directory = sys.argv[1]
    use_threading = "--single-threaded" not in sys.argv
    
    # Parse delay argument
    delay = 0
    if "--delay" in sys.argv:
        idx = sys.argv.index("--delay")
        if idx + 1 < len(sys.argv):
            try:
                delay = float(sys.argv[idx + 1])
            except ValueError:
                print("Invalid delay value")
                sys.exit(1)
    
    # Set counter safety flag
    if "--unsafe-counter" in sys.argv:
        USE_THREAD_SAFE_COUNTER = False
        print("WARNING: Running with unsafe counter (race conditions possible)")
    
    if "--race-demo" in sys.argv:
        SIMULATE_RACE_CONDITION = True
        print("WARNING: Race condition simulation enabled")
    
    run_server(directory, use_threading=use_threading, delay=delay)
