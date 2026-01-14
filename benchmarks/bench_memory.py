#!/usr/bin/env python3
"""
Memory allocation benchmark for serialization.
Tracks both Python (tracemalloc) and Rust (alloc-stats) heap allocations.
"""
import gc
import tracemalloc
from bench_serialization import (
    TransactionData, TRANSACTION, TRANSACTIONS,
    DATA, DATA_MANY,
)
import marshmallow_recipe as mr


def has_rust_alloc_stats():
    """Check if Rust alloc-stats feature is enabled."""
    return hasattr(mr.nuked.nuked, 'reset_alloc_stats')


def measure_allocs(func, warmup=5, iterations=10):
    """Measure both Rust and Python heap allocations."""
    has_rust = has_rust_alloc_stats()

    # Warmup
    for _ in range(warmup):
        func()

    gc.collect()

    # Start tracking
    if has_rust:
        mr.nuked.nuked.reset_alloc_stats()
    tracemalloc.start()

    for _ in range(iterations):
        func()

    # Get Python stats
    py_current, py_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Get Rust stats
    if has_rust:
        rust_alloc, rust_dealloc, rust_n, rust_dn = mr.nuked.nuked.get_alloc_stats()
        rust_alloc //= iterations
        rust_dealloc //= iterations
        rust_n //= iterations
        rust_dn //= iterations
    else:
        rust_alloc = rust_dealloc = rust_n = rust_dn = 0

    return {
        'rust_bytes': rust_alloc,
        'rust_dealloc': rust_dealloc,
        'rust_allocs': rust_n,
        'rust_deallocs': rust_dn,
        'python_peak': py_peak,
    }


def print_stats(name, stats):
    """Print allocation statistics."""
    print(f"\n{name}:")
    print(f"  Rust:   {stats['rust_bytes']:,} bytes ({stats['rust_allocs']} allocs)")
    print(f"  Python: {stats['python_peak']:,} bytes (peak)")
    print(f"  Total:  {stats['rust_bytes'] + stats['python_peak']:,} bytes")


def main():
    print("=" * 60)
    print("Memory Allocation Benchmark (Rust + Python)")
    print("=" * 60)

    if not has_rust_alloc_stats():
        print("\nWARNING: Rust alloc-stats not enabled. Showing Python only.")
        print("Run: uv run maturin develop --release --features alloc-stats")

    print("\n--- Single Object Serialization (avg over 10 calls) ---")

    stats = measure_allocs(lambda: mr.nuked.dump_to_bytes(TransactionData, TRANSACTION))
    print_stats("nuked_dump_to_bytes", stats)

    stats = measure_allocs(lambda: mr.nuked.load_from_bytes(TransactionData, DATA))
    print_stats("nuked_load_from_bytes", stats)

    print("\n--- Batch (100 items) Serialization ---")

    stats = measure_allocs(lambda: mr.nuked.dump_to_bytes(list[TransactionData], TRANSACTIONS))
    print_stats("nuked_dump_to_bytes_many", stats)

    stats = measure_allocs(lambda: mr.nuked.load_from_bytes(list[TransactionData], DATA_MANY))
    print_stats("nuked_load_from_bytes_many", stats)


if __name__ == "__main__":
    main()
