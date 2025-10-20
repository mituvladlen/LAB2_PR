import sys
import os
import socket

# Socket read chunk size (bytes) when receiving the HTTP response
BUFFER_SIZE = 8192

def http_get(host: str, port: int, path: str) -> bytes:
    """Open a TCP connection and perform a minimal HTTP/1.1 GET for (host, port, path)."""
    # Build minimal HTTP/1.1 GET request
    if not path.startswith("/"):
        path = "/" + path
    req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(req.encode("utf-8"))
        chunks = []
        while True:
            data = s.recv(BUFFER_SIZE)
            if not data:
                break
            chunks.append(data)
    return b"".join(chunks)


def parse_http_response(raw: bytes):
    """Parse raw HTTP response bytes into (status_code, headers dict, body bytes)."""
    # Split headers and body
    sep = raw.find(b"\r\n\r\n")
    if sep == -1:
        raise ValueError("Invalid HTTP response: no header/body separator")
    head = raw[:sep].decode("iso-8859-1", errors="replace")
    body = raw[sep+4:]

    # Status line
    lines = head.split("\r\n")
    status_line = lines[0]
    parts = status_line.split(" ", 2)
    if len(parts) < 2:
        raise ValueError("Invalid status line")
    status_code = int(parts[1])

    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()

    return status_code, headers, body


def main():
    """CLI entry: download/print based on content-type (HTML prints, PNG/PDF save)."""
    if len(sys.argv) != 5:
        print("Usage: python client.py server_host server_port url_path directory")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    path = sys.argv[3]
    out_dir = sys.argv[4]

    raw = http_get(host, port, path)
    status, headers, body = parse_http_response(raw)

    ctype = headers.get("content-type", "")

    if status != 200:
        print(f"HTTP {status}")
        sys.exit(0)

    if ctype.startswith("text/html"):
        # Print HTML body
        try:
            print(body.decode("utf-8", errors="replace"))
        except UnicodeDecodeError:
            # Fallback raw print
            sys.stdout.buffer.write(body)
        return

    if ctype in ("image/png", "application/pdf"):
        os.makedirs(out_dir, exist_ok=True)
        # Determine filename from path
        name = path.strip("/").split("/")[-1] or "index"
        # Add extension if missing (rare)
        if ctype == "image/png" and not name.lower().endswith(".png"):
            name += ".png"
        if ctype == "application/pdf" and not name.lower().endswith(".pdf"):
            name += ".pdf"
        out_path = os.path.join(out_dir, name)
        with open(out_path, "wb") as f:
            f.write(body)
        print(f"Saved to {out_path}")
        return

    print(f"Unhandled content-type: {ctype}")


if __name__ == "__main__":
    main()
