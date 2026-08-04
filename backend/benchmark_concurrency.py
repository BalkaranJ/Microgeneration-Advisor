"""
Standalone benchmark for the /assess concurrency optimization in solar.py.
Times fetch_building_insights (Google Solar) + fetch_daily_irradiance (NASA
POWER) run sequentially vs concurrently (asyncio.gather) against the real
APIs, for one sample address. Run manually: python benchmark_concurrency.py
"""
import asyncio
import time

from irradiance import fetch_daily_irradiance
from solar import fetch_building_insights

LAT, LON = 51.0447, -114.0719  # Calgary, AB


async def sequential():
    start = time.perf_counter()
    await fetch_building_insights(LAT, LON)
    await fetch_daily_irradiance(LAT, LON)
    return time.perf_counter() - start


async def concurrent():
    start = time.perf_counter()
    await asyncio.gather(fetch_building_insights(LAT, LON), fetch_daily_irradiance(LAT, LON))
    return time.perf_counter() - start


async def main():
    runs = 3
    seq_times = []
    con_times = []
    for _ in range(runs):
        seq_times.append(await sequential())
        con_times.append(await concurrent())

    seq_avg = sum(seq_times) / runs
    con_avg = sum(con_times) / runs

    print(f"Sequential (await, await):     {[f'{t:.3f}s' for t in seq_times]}  avg {seq_avg:.3f}s")
    print(f"Concurrent (asyncio.gather):   {[f'{t:.3f}s' for t in con_times]}  avg {con_avg:.3f}s")
    print(f"Reduction:                      {(1 - con_avg / seq_avg) * 100:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
