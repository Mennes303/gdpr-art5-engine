"""
Simple asyncio-based load generator for the ``/decision`` endpoint.

* Spawns ``CONN`` concurrent clients for ``SECS`` seconds.
* Prints p50 / p95 / p99 latencies and overall throughput.
* Request body is loaded from *payload.json* in the current directory.
"""

import asyncio
import json
import pathlib
import statistics
import time

import httpx

URL = "http://127.0.0.1:8000/decision"
BODY = json.loads(pathlib.Path("payload.json").read_text())
CONN = 100  # concurrent clients
SECS = 60   # test duration
latencies: list[float] = []


async def worker() -> None:
    """Issue POST requests in a loop until the global timer expires."""
    async with httpx.AsyncClient(timeout=10) as client:
        stop_at = time.perf_counter() + SECS
        while time.perf_counter() < stop_at:
            t0 = time.perf_counter()
            await client.post(URL, json=BODY)
            latencies.append((time.perf_counter() - t0) * 1000)  # ms


async def main() -> None:
    await asyncio.gather(*(worker() for _ in range(CONN)))


if __name__ == "__main__":
    asyncio.run(main())
    p50, p95, p99 = [statistics.quantiles(latencies, n=100)[i] for i in (49, 94, 98)]
    print(f"p50={p50:.2f} ms  p95={p95:.2f} ms  p99={p99:.2f} ms")
    print(f"Throughput = {len(latencies)/SECS:,.0f} req/s")
