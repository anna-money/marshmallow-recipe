import dataclasses
import datetime
import decimal
import enum
import json
import timeit
import uuid

import marshmallow_recipe as mr


class Priority(int, enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Status(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


@dataclasses.dataclass(slots=True, kw_only=True)
class SimpleTypes:
    name: str
    age: int
    score: float
    active: bool


@dataclasses.dataclass(slots=True, kw_only=True)
class Address:
    city: str
    country: str
    zip_code: str


@dataclasses.dataclass(slots=True, kw_only=True)
class UserWithAddress:
    name: str
    age: int
    email: str
    address: Address


@dataclasses.dataclass(slots=True, kw_only=True)
class Product:
    id: int
    name: str
    price: decimal.Decimal
    tags: list[str]


@dataclasses.dataclass(slots=True, kw_only=True)
class Order:
    order_id: int
    customer_name: str
    products: list[Product]
    metadata: dict[str, str]


@dataclasses.dataclass(slots=True, kw_only=True)
class ComplexEntity:
    id: uuid.UUID
    name: str
    created_at: datetime.datetime
    amount: decimal.Decimal
    priority: Priority
    status: Status
    tags: list[str]
    attributes: dict[str, str]


def benchmark(func, number: int = 100) -> dict:
    time_taken = timeit.timeit(func, number=number)
    avg_time = time_taken / number
    return {
        "total_time": time_taken,
        "avg_time_ms": avg_time * 1000,
        "ops_per_sec": number / time_taken,
    }


def run_benchmarks():
    print("=" * 80)
    print("SPEEDUP vs MARSHMALLOW BENCHMARK")
    print("=" * 80)
    print()
    print("Methods compared:")
    print("  LOAD:")
    print("    marshmallow: bytes → json.loads() → dict → mr.load() → obj")
    print("    speedup:     bytes → serde Visitor → obj (no intermediate)")
    print("  DUMP:")
    print("    marshmallow: obj → mr.dump() → dict → json.dumps() → bytes")
    print("    speedup:     obj → serde Serialize → bytes (no intermediate)")
    print()
    print("=" * 80)

    test_cases = {
        "simple": (
            SimpleTypes,
            SimpleTypes(name="John Doe", age=30, score=95.5, active=True),
        ),
        "nested": (
            UserWithAddress,
            UserWithAddress(
                name="Jane Smith",
                age=28,
                email="jane@example.com",
                address=Address(city="New York", country="USA", zip_code="10001"),
            ),
        ),
        "with_collections": (
            Order,
            Order(
                order_id=12345,
                customer_name="John Customer",
                products=[
                    Product(id=1, name="Laptop", price=decimal.Decimal("999.99"), tags=["electronics", "computers"]),
                    Product(id=2, name="Mouse", price=decimal.Decimal("29.99"), tags=["electronics", "peripherals"]),
                    Product(id=3, name="Keyboard", price=decimal.Decimal("79.99"), tags=["electronics", "peripherals"]),
                ],
                metadata={"source": "web", "region": "US", "user_tier": "premium"},
            ),
        ),
        "complex_types": (
            ComplexEntity,
            ComplexEntity(
                id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
                name="Test Entity",
                created_at=datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC),
                amount=decimal.Decimal("1234.56"),
                priority=Priority.HIGH,
                status=Status.ACTIVE,
                tags=["important", "urgent", "review"],
                attributes={"owner": "admin", "department": "engineering"},
            ),
        ),
    }

    list_simple_100 = [
        SimpleTypes(name=f"User{i}", age=20 + i, score=80.0 + i, active=i % 2 == 0) for i in range(100)
    ]

    list_simple_1000 = [
        SimpleTypes(name=f"User{i}", age=20 + i % 80, score=80.0 + i % 20, active=i % 2 == 0) for i in range(1000)
    ]

    list_complex_100 = [
        ComplexEntity(
            id=uuid.uuid4(),
            name=f"Entity{i}",
            created_at=datetime.datetime(2024, 1, i % 28 + 1, 10, 30, 0, tzinfo=datetime.UTC),
            amount=decimal.Decimal(f"{100 + i}.{i % 100:02d}"),
            priority=Priority(i % 3 + 1),
            status=list(Status)[i % 3],
            tags=[f"tag{j}" for j in range(i % 5 + 1)],
            attributes={f"attr{j}": f"value{j}" for j in range(i % 3 + 1)},
        )
        for i in range(100)
    ]

    load_results = []
    dump_results = []

    print("Warming up caches...")
    for name, (cls, data) in test_cases.items():
        json_bytes = mr.speedup.dump(cls, data)
        mr.speedup.load(cls, json_bytes)
        mr.load(cls, json.loads(json_bytes.decode()))
        json.dumps(mr.dump(cls, data)).encode()

    for cls, data_list in [(list[SimpleTypes], list_simple_100), (list[SimpleTypes], list_simple_1000), (list[ComplexEntity], list_complex_100)]:
        json_bytes = mr.speedup.dump(cls, data_list)
        mr.speedup.load(cls, json_bytes)

    print("Running benchmarks...")
    print()

    print("=" * 80)
    print("LOAD BENCHMARK")
    print("=" * 80)
    print()

    for name, (cls, data) in test_cases.items():
        json_bytes = mr.speedup.dump(cls, data)

        marshmallow_result = benchmark(lambda: mr.load(cls, json.loads(json_bytes.decode())), number=1000)
        speedup_result = benchmark(lambda: mr.speedup.load(cls, json_bytes), number=1000)

        load_results.append({
            "name": name,
            "size_bytes": len(json_bytes),
            "marshmallow": marshmallow_result,
            "speedup": speedup_result,
        })

    list_cases = [
        ("list_simple_100", list[SimpleTypes], list_simple_100),
        ("list_simple_1000", list[SimpleTypes], list_simple_1000),
        ("list_complex_100", list[ComplexEntity], list_complex_100),
    ]

    for name, cls, data_list in list_cases:
        json_bytes = mr.speedup.dump(cls, data_list)

        speedup_result = benchmark(lambda: mr.speedup.load(cls, json_bytes), number=100)

        load_results.append({
            "name": name,
            "size_bytes": len(json_bytes),
            "marshmallow": None,
            "speedup": speedup_result,
        })

    print(f"{'Scenario':<25} {'Size':<10} {'marshmallow':<15} {'speedup':<15} {'speedup ratio':<15}")
    print("-" * 80)

    for r in load_results:
        name = r["name"]
        size = f"{r['size_bytes']}b"
        mm_time = f"{r['marshmallow']['avg_time_ms']:.3f}ms" if r["marshmallow"] else "N/A"
        speedup_time = f"{r['speedup']['avg_time_ms']:.3f}ms"
        if r["marshmallow"]:
            ratio = r["marshmallow"]["avg_time_ms"] / r["speedup"]["avg_time_ms"]
            ratio_str = f"{ratio:.1f}x faster"
        else:
            ratio_str = "N/A"
        print(f"{name:<25} {size:<10} {mm_time:<15} {speedup_time:<15} {ratio_str:<15}")

    print()
    print("=" * 80)
    print("DUMP BENCHMARK")
    print("=" * 80)
    print()

    for name, (cls, data) in test_cases.items():
        marshmallow_result = benchmark(lambda: json.dumps(mr.dump(cls, data)).encode(), number=1000)
        speedup_result = benchmark(lambda: mr.speedup.dump(cls, data), number=1000)

        dump_results.append({
            "name": name,
            "marshmallow": marshmallow_result,
            "speedup": speedup_result,
        })

    for name, cls, data_list in list_cases:
        speedup_result = benchmark(lambda: mr.speedup.dump(cls, data_list), number=100)

        dump_results.append({
            "name": name,
            "marshmallow": None,
            "speedup": speedup_result,
        })

    print(f"{'Scenario':<25} {'marshmallow':<15} {'speedup':<15} {'speedup ratio':<15}")
    print("-" * 70)

    for r in dump_results:
        name = r["name"]
        mm_time = f"{r['marshmallow']['avg_time_ms']:.3f}ms" if r["marshmallow"] else "N/A"
        speedup_time = f"{r['speedup']['avg_time_ms']:.3f}ms"
        if r["marshmallow"]:
            ratio = r["marshmallow"]["avg_time_ms"] / r["speedup"]["avg_time_ms"]
            ratio_str = f"{ratio:.1f}x faster"
        else:
            ratio_str = "N/A"
        print(f"{name:<25} {mm_time:<15} {speedup_time:<15} {ratio_str:<15}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    load_mm_results = [r for r in load_results if r["marshmallow"]]
    load_avg_ratio = sum(r["marshmallow"]["avg_time_ms"] / r["speedup"]["avg_time_ms"] for r in load_mm_results) / len(load_mm_results)

    dump_mm_results = [r for r in dump_results if r["marshmallow"]]
    dump_avg_ratio = sum(r["marshmallow"]["avg_time_ms"] / r["speedup"]["avg_time_ms"] for r in dump_mm_results) / len(dump_mm_results)

    print(f"LOAD: speedup is {load_avg_ratio:.1f}x faster than marshmallow on average")
    print(f"DUMP: speedup is {dump_avg_ratio:.1f}x faster than marshmallow on average")
    print()


if __name__ == "__main__":
    run_benchmarks()
