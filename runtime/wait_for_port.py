"""Wait until a local TCP port is accepting connections."""
import socket
import sys
import time


def wait_for_port(port: int, timeout_seconds: float = 30.0, poll_interval: float = 0.25) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                return
        except OSError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Port {port} did not become ready within {timeout_seconds} seconds")
            time.sleep(poll_interval)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9876
    timeout = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    wait_for_port(port, timeout)
