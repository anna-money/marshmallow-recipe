import dataclasses
import json
import timeit
from typing import Annotated

import marshmallow_recipe as mr


@dataclasses.dataclass
class SimpleTypes:
    name: str
    age: int
    score: float
    active: bool


@dataclasses.dataclass
class Address:
    city: str
    country: str
    zip_code: str


@dataclasses.dataclass
class UserWithAddress:
    name: str
    age: int
    email: str
    address: Address


@dataclasses.dataclass
class Product:
    id: int
    name: str
    price: float
    tags: list[str]


@dataclasses.dataclass
class Order:
    order_id: int
    customer_name: str
    products: list[Product]
    metadata: dict[str, str]


def benchmark(name: str, func, number: int = 100):
    """Run a benchmark and print results."""
    time_taken = timeit.timeit(func, number=number)
    avg_time = time_taken / number
    return {
        "name": name,
        "total_time": time_taken,
        "avg_time": avg_time,
        "number": number,
    }


def run_benchmarks():
    """Run all benchmarks comparing v1 vs v2."""
    results = []

    print("=" * 80)
    print("MARSHMALLOW_RECIPE PERFORMANCE COMPARISON: v1 vs v2")
    print("=" * 80)
    print("Fair Comparison (Complete JSON Serialization Cycle):")
    print("  v1 dump: obj → dump(obj) → dict → json.dumps() → str → encode() → bytes")
    print("  v1 load: bytes → decode() → str → json.loads() → dict → load(dict) → obj")
    print("  v2 dump: dump(cls, obj) → bytes (direct)")
    print("  v2 load: load(cls, bytes) → obj (direct)")
    print("=" * 80)
    print()

    test_data = {
        "simple_types": SimpleTypes(name="John Doe", age=30, score=95.5, active=True),
        "nested": UserWithAddress(
            name="Jane Smith",
            age=28,
            email="jane@example.com",
            address=Address(city="New York", country="USA", zip_code="10001"),
        ),
        "complex": Order(
            order_id=12345,
            customer_name="John Customer",
            products=[
                Product(id=1, name="Laptop", price=999.99, tags=["electronics", "computers"]),
                Product(id=2, name="Mouse", price=29.99, tags=["electronics", "peripherals"]),
                Product(id=3, name="Keyboard", price=79.99, tags=["electronics", "peripherals"]),
            ],
            metadata={"source": "web", "region": "US", "user_tier": "premium"},
        ),
    }

    list_simple = [
        SimpleTypes(name=f"User{i}", age=20 + i, score=80.0 + i, active=i % 2 == 0)
        for i in range(100)
    ]

    list_nested = [
        UserWithAddress(
            name=f"User{i}",
            age=20 + i,
            email=f"user{i}@example.com",
            address=Address(city=f"City{i}", country="USA", zip_code=f"1000{i}"),
        )
        for i in range(50)
    ]

    simple_types_dumped_v1 = json.dumps(mr.dump(SimpleTypes, test_data["simple_types"])).encode()
    simple_types_dumped_v2 = mr.speedup.dump(SimpleTypes, test_data["simple_types"])
    nested_dumped_v1 = json.dumps(mr.dump(UserWithAddress, test_data["nested"])).encode()
    nested_dumped_v2 = mr.speedup.dump(UserWithAddress, test_data["nested"])
    complex_dumped_v1 = json.dumps(mr.dump(Order, test_data["complex"])).encode()
    complex_dumped_v2 = mr.speedup.dump(Order, test_data["complex"])
    list_simple_dumped_v1 = json.dumps(mr.dump_many(list_simple)).encode()
    list_simple_dumped_v2 = mr.speedup.dump(list[SimpleTypes], list_simple)
    list_nested_dumped_v1 = json.dumps(mr.dump_many(list_nested)).encode()
    list_nested_dumped_v2 = mr.speedup.dump(list[UserWithAddress], list_nested)

    benchmark_tests = [
        ("Simple Types - Dump", lambda: json.dumps(mr.dump(SimpleTypes, test_data["simple_types"])).encode()),
        ("Simple Types - Dump (v2)", lambda: mr.speedup.dump(SimpleTypes, test_data["simple_types"])),
        ("Simple Types - Load", lambda: mr.load(SimpleTypes, json.loads(simple_types_dumped_v1.decode()))),
        (
            "Simple Types - Load (v2)",
            lambda: mr.speedup.load(SimpleTypes, simple_types_dumped_v2),
        ),
        ("Nested - Dump", lambda: json.dumps(mr.dump(UserWithAddress, test_data["nested"])).encode()),
        ("Nested - Dump (v2)", lambda: mr.speedup.dump(UserWithAddress, test_data["nested"])),
        (
            "Nested - Load",
            lambda: mr.load(UserWithAddress, json.loads(nested_dumped_v1.decode())),
        ),
        (
            "Nested - Load (v2)",
            lambda: mr.speedup.load(UserWithAddress, nested_dumped_v2),
        ),
        ("Complex - Dump", lambda: json.dumps(mr.dump(Order, test_data["complex"])).encode()),
        ("Complex - Dump (v2)", lambda: mr.speedup.dump(Order, test_data["complex"])),
        (
            "Complex - Load",
            lambda: mr.load(Order, json.loads(complex_dumped_v1.decode())),
        ),
        (
            "Complex - Load (v2)",
            lambda: mr.speedup.load(Order, complex_dumped_v2),
        ),
        ("List[SimpleTypes] (100 items) - Dump", lambda: json.dumps(mr.dump_many(list_simple)).encode()),
        (
            "List[SimpleTypes] (100 items) - Dump (v2)",
            lambda: mr.speedup.dump(list[SimpleTypes], list_simple),
        ),
        (
            "List[SimpleTypes] (100 items) - Load",
            lambda: mr.load_many(SimpleTypes, json.loads(list_simple_dumped_v1.decode())),
        ),
        (
            "List[SimpleTypes] (100 items) - Load (v2)",
            lambda: mr.speedup.load(list[SimpleTypes], list_simple_dumped_v2),
        ),
        ("List[Nested] (50 items) - Dump", lambda: json.dumps(mr.dump_many(list_nested)).encode()),
        (
            "List[Nested] (50 items) - Dump (v2)",
            lambda: mr.speedup.dump(list[UserWithAddress], list_nested),
        ),
        (
            "List[Nested] (50 items) - Load",
            lambda: mr.load_many(UserWithAddress, json.loads(list_nested_dumped_v1.decode())),
        ),
        (
            "List[Nested] (50 items) - Load (v2)",
            lambda: mr.speedup.load(list[UserWithAddress], list_nested_dumped_v2),
        ),
    ]

    # Run benchmarks with warmup
    print("Warming up caches...")
    for name, func in benchmark_tests:
        try:
            func()
        except Exception as e:
            print(f"Error in warmup for {name}: {e}")
    print()

    print("Running benchmarks...")
    for name, func in benchmark_tests:
        try:
            result = benchmark(name, func, number=100)
            results.append(result)
            status = "✓"
        except Exception as e:
            print(f"  {name}: ERROR - {e}")
            results.append(
                {
                    "name": name,
                    "error": str(e),
                }
            )
            status = "✗"
        if status == "✓":
            print(f"  {status} {name}: {result['avg_time']*1000:.3f}ms")

    print()
    print("=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print()

    def group_results(results):
        """Group results by scenario."""
        grouped = {}
        for result in results:
            if "error" in result:
                continue
            parts = result["name"].rsplit(" - ", 1)
            if len(parts) != 2:
                continue
            scenario, operation = parts
            scenario = scenario.replace(" (v2)", "")

            if scenario not in grouped:
                grouped[scenario] = {}
            if "(v2)" in result["name"]:
                grouped[scenario]["v2"] = result
            else:
                grouped[scenario]["v1"] = result
        return grouped

    grouped = group_results(results)

    print(f"{'Scenario':<40} {'v1 (ms)':<12} {'v2 (ms)':<12} {'Speedup':<10}")
    print("-" * 74)

    v2_faster_count = 0
    v1_faster_count = 0

    for scenario in sorted(grouped.keys()):
        operations = grouped[scenario]
        if "v1" in operations and "v2" in operations:
            v1_time = operations["v1"]["avg_time"] * 1000
            v2_time = operations["v2"]["avg_time"] * 1000
            speedup = v1_time / v2_time

            speedup_str = f"{speedup:.2f}x"
            if speedup > 1:
                speedup_indicator = "v2↑"
                v2_faster_count += 1
            else:
                speedup_indicator = "v1↑"
                v1_faster_count += 1
                speedup_str = f"{1/speedup:.2f}x v1"

            print(f"{scenario:<40} {v1_time:<12.3f} {v2_time:<12.3f} {speedup_str:<10} {speedup_indicator}")

    print()
    print(f"v2 is faster: {v2_faster_count} scenarios")
    print(f"v1 is faster: {v1_faster_count} scenarios")
    print()

    print("=" * 80)
    print("DETAILED METRICS")
    print("=" * 80)
    print()

    for scenario in sorted(grouped.keys()):
        operations = grouped[scenario]
        if "v1" in operations and "v2" in operations:
            print(f"{scenario}:")
            print(f"  v1: {operations['v1']['avg_time']*1000:.3f}ms (total: {operations['v1']['total_time']:.3f}s)")
            print(f"  v2: {operations['v2']['avg_time']*1000:.3f}ms (total: {operations['v2']['total_time']:.3f}s)")
            speedup = operations["v1"]["avg_time"] / operations["v2"]["avg_time"]
            print(f"  Speedup: {speedup:.2f}x" if speedup > 1 else f"  v1 is {1/speedup:.2f}x slower")
            print()


if __name__ == "__main__":
    run_benchmarks()
