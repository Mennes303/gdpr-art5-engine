import asyncio
import httpx
import json
import statistics
import time
import pathlib

# Benchmark configuration
URL = "http://127.0.0.1:8000/decision"
BODY = json.loads(pathlib.Path("payload.json").read_text())
CONN = 100
SECS = 60
latencies: list[float] = []

async def worker() -> None:
    """
    Single worker sending POST requests in a loop until time expires.
    Records each request latency in milliseconds.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        end_time = time.perf_counter() + SECS
        while time.perf_counter() < end_time:
            start = time.perf_counter()
            await client.post(URL, json=BODY)
            latencies.append((time.perf_counter() - start) * 1000)

async def main() -> None:
    """
    Launch CONN workers concurrently and wait until they complete.
    """
    await asyncio.gather(*(worker() for _ in range(CONN)))

if __name__ == "__main__":
    # Run the benchmark
    asyncio.run(main())

    # Compute latency percentiles
    p50, p95, p99 = [statistics.quantiles(latencies, n=100)[i] for i in (49, 94, 98)]

    # Print summary
    print(f"p50={p50:.2f} ms  p95={p95:.2f} ms  p99={p99:.2f} ms")
    print(f"Throughput = {len(latencies)/SECS:,.0f} req/s")