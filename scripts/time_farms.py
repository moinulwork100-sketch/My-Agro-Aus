"""
Timing harness for GET /api/farms — run before and after the N+1 fix.
Usage: python scripts/time_farms.py [--url http://localhost:8000] [--n 10]
"""
import argparse
import statistics
import time
import urllib.request


def fetch_once(url: str) -> float:
    start = time.perf_counter()
    with urllib.request.urlopen(url, timeout=120) as resp:
        resp.read()
    return (time.perf_counter() - start) * 1000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000/api/farms")
    parser.add_argument("--n", type=int, default=10)
    args = parser.parse_args()

    print(f"Timing {args.n} calls -> {args.url}")

    cold = fetch_once(args.url)
    print(f"  cold/first call : {cold:8.0f} ms")

    times: list[float] = []
    for i in range(args.n):
        ms = fetch_once(args.url)
        times.append(ms)
        print(f"  call {i+1:2d}         : {ms:8.0f} ms")

    print()
    print(f"  min    : {min(times):8.0f} ms")
    print(f"  median : {statistics.median(times):8.0f} ms")
    print(f"  max    : {max(times):8.0f} ms")
    print(f"  mean   : {statistics.mean(times):8.0f} ms")


if __name__ == "__main__":
    main()
