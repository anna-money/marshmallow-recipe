import dataclasses
import json
import timeit

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True)
class WideDataclass:
    field_00: str
    field_01: str
    field_02: str
    field_03: str
    field_04: str
    field_05: str
    field_06: str
    field_07: str
    field_08: str
    field_09: str
    field_10: str
    field_11: str
    field_12: str
    field_13: str
    field_14: str
    field_15: str
    field_16: str
    field_17: str
    field_18: str
    field_19: str
    field_20: str
    field_21: str
    field_22: str
    field_23: str
    field_24: str
    field_25: str
    field_26: str
    field_27: str
    field_28: str
    field_29: str
    field_30: str
    field_31: str
    field_32: str
    field_33: str
    field_34: str
    field_35: str
    field_36: str
    field_37: str
    field_38: str
    field_39: str
    field_40: str
    field_41: str
    field_42: str
    field_43: str
    field_44: str
    field_45: str
    field_46: str
    field_47: str
    field_48: str
    field_49: str
    field_50: str
    field_51: str
    field_52: str
    field_53: str
    field_54: str
    field_55: str
    field_56: str
    field_57: str
    field_58: str
    field_59: str
    field_60: str
    field_61: str
    field_62: str
    field_63: str
    field_64: str
    field_65: str
    field_66: str
    field_67: str
    field_68: str
    field_69: str
    field_70: str
    field_71: str
    field_72: str
    field_73: str
    field_74: str
    field_75: str
    field_76: str
    field_77: str
    field_78: str
    field_79: str
    field_80: str
    field_81: str
    field_82: str
    field_83: str
    field_84: str
    field_85: str
    field_86: str
    field_87: str
    field_88: str
    field_89: str
    field_90: str
    field_91: str
    field_92: str
    field_93: str
    field_94: str
    field_95: str
    field_96: str
    field_97: str
    field_98: str
    field_99: str


@dataclasses.dataclass(frozen=True, slots=True)
class WideContainer:
    items: list[WideDataclass]


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
    time_taken = timeit.timeit(func, number=number)
    avg_time = time_taken / number
    return {
        "name": name,
        "total_time": time_taken,
        "avg_time": avg_time,
        "number": number,
    }


def run_benchmarks():
    results = []

    print("=" * 90)
    print("MARSHMALLOW_RECIPE PERFORMANCE COMPARISON")
    print("=" * 90)
    print("Implementations:")
    print("  marshmallow:    obj → mr.dump() → dict → json.dumps() → bytes")
    print("  speedup_bytes:  obj → dump_to_bytes() → bytes (Rust JSON)")
    print("  speedup:        obj → dump() → dict → json.dumps() → bytes (Rust + Python JSON)")
    print("=" * 90)
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
        SimpleTypes(name=f"User{i}", age=20 + i, score=80.0 + i, active=i % 2 == 0) for i in range(100)
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

    wide_items = [
        WideDataclass(**{f"field_{j:02d}": f"value_{i}_{j}" for j in range(100)})
        for i in range(100)
    ]
    wide_container = WideContainer(items=wide_items)

    simple_bytes = mr.speedup.dump_to_bytes(SimpleTypes, test_data["simple_types"])
    nested_bytes = mr.speedup.dump_to_bytes(UserWithAddress, test_data["nested"])
    complex_bytes = mr.speedup.dump_to_bytes(Order, test_data["complex"])
    list_simple_bytes = mr.speedup.dump_to_bytes(list[SimpleTypes], list_simple)
    list_nested_bytes = mr.speedup.dump_to_bytes(list[UserWithAddress], list_nested)
    wide_bytes = mr.speedup.dump_to_bytes(WideContainer, wide_container)

    benchmark_tests = [
        ("Simple - Dump [marshmallow]", lambda: json.dumps(mr.dump(SimpleTypes, test_data["simple_types"])).encode()),
        ("Simple - Dump [speedup_bytes]", lambda: mr.speedup.dump_to_bytes(SimpleTypes, test_data["simple_types"])),
        ("Simple - Dump [speedup]", lambda: json.dumps(mr.speedup.dump(SimpleTypes, test_data["simple_types"])).encode()),
        ("Simple - Load [marshmallow]", lambda: mr.load(SimpleTypes, json.loads(simple_bytes))),
        ("Simple - Load [speedup_bytes]", lambda: mr.speedup.load_from_bytes(SimpleTypes, simple_bytes)),
        ("Simple - Load [speedup]", lambda: mr.speedup.load(SimpleTypes, json.loads(simple_bytes))),
        ("Nested - Dump [marshmallow]", lambda: json.dumps(mr.dump(UserWithAddress, test_data["nested"])).encode()),
        ("Nested - Dump [speedup_bytes]", lambda: mr.speedup.dump_to_bytes(UserWithAddress, test_data["nested"])),
        ("Nested - Dump [speedup]", lambda: json.dumps(mr.speedup.dump(UserWithAddress, test_data["nested"])).encode()),
        ("Nested - Load [marshmallow]", lambda: mr.load(UserWithAddress, json.loads(nested_bytes))),
        ("Nested - Load [speedup_bytes]", lambda: mr.speedup.load_from_bytes(UserWithAddress, nested_bytes)),
        ("Nested - Load [speedup]", lambda: mr.speedup.load(UserWithAddress, json.loads(nested_bytes))),
        ("Complex - Dump [marshmallow]", lambda: json.dumps(mr.dump(Order, test_data["complex"])).encode()),
        ("Complex - Dump [speedup_bytes]", lambda: mr.speedup.dump_to_bytes(Order, test_data["complex"])),
        ("Complex - Dump [speedup]", lambda: json.dumps(mr.speedup.dump(Order, test_data["complex"])).encode()),
        ("Complex - Load [marshmallow]", lambda: mr.load(Order, json.loads(complex_bytes))),
        ("Complex - Load [speedup_bytes]", lambda: mr.speedup.load_from_bytes(Order, complex_bytes)),
        ("Complex - Load [speedup]", lambda: mr.speedup.load(Order, json.loads(complex_bytes))),
        ("List[Simple] 100 - Dump [marshmallow]", lambda: json.dumps(mr.dump_many(list_simple)).encode()),
        ("List[Simple] 100 - Dump [speedup_bytes]", lambda: mr.speedup.dump_to_bytes(list[SimpleTypes], list_simple)),
        ("List[Simple] 100 - Dump [speedup]", lambda: json.dumps(mr.speedup.dump(list[SimpleTypes], list_simple)).encode()),
        ("List[Simple] 100 - Load [marshmallow]", lambda: mr.load_many(SimpleTypes, json.loads(list_simple_bytes))),
        ("List[Simple] 100 - Load [speedup_bytes]", lambda: mr.speedup.load_from_bytes(list[SimpleTypes], list_simple_bytes)),
        ("List[Simple] 100 - Load [speedup]", lambda: mr.speedup.load(list[SimpleTypes], json.loads(list_simple_bytes))),
        ("List[Nested] 50 - Dump [marshmallow]", lambda: json.dumps(mr.dump_many(list_nested)).encode()),
        ("List[Nested] 50 - Dump [speedup_bytes]", lambda: mr.speedup.dump_to_bytes(list[UserWithAddress], list_nested)),
        ("List[Nested] 50 - Dump [speedup]", lambda: json.dumps(mr.speedup.dump(list[UserWithAddress], list_nested)).encode()),
        ("List[Nested] 50 - Load [marshmallow]", lambda: mr.load_many(UserWithAddress, json.loads(list_nested_bytes))),
        ("List[Nested] 50 - Load [speedup_bytes]", lambda: mr.speedup.load_from_bytes(list[UserWithAddress], list_nested_bytes)),
        ("List[Nested] 50 - Load [speedup]", lambda: mr.speedup.load(list[UserWithAddress], json.loads(list_nested_bytes))),
        ("Wide 100x100 - Dump [marshmallow]", lambda: json.dumps(mr.dump(WideContainer, wide_container)).encode()),
        ("Wide 100x100 - Dump [speedup_bytes]", lambda: mr.speedup.dump_to_bytes(WideContainer, wide_container)),
        ("Wide 100x100 - Dump [speedup]", lambda: json.dumps(mr.speedup.dump(WideContainer, wide_container)).encode()),
        ("Wide 100x100 - Load [marshmallow]", lambda: mr.load(WideContainer, json.loads(wide_bytes))),
        ("Wide 100x100 - Load [speedup_bytes]", lambda: mr.speedup.load_from_bytes(WideContainer, wide_bytes)),
        ("Wide 100x100 - Load [speedup]", lambda: mr.speedup.load(WideContainer, json.loads(wide_bytes))),
    ]

    print("Warming up...")
    for name, func in benchmark_tests:
        func()
    print()

    print("Running benchmarks...")
    for name, func in benchmark_tests:
        result = benchmark(name, func, number=100)
        results.append(result)
        print(f"  {name}: {result['avg_time']*1000:.3f}ms")

    print()
    print("=" * 90)
    print("RESULTS SUMMARY")
    print("=" * 90)
    print()

    def group_results(results):
        grouped = {}
        for result in results:
            name = result["name"]
            if "[marshmallow]" in name:
                scenario = name.replace(" [marshmallow]", "")
                impl = "marshmallow"
            elif "[speedup_bytes]" in name:
                scenario = name.replace(" [speedup_bytes]", "")
                impl = "speedup_bytes"
            elif "[speedup]" in name:
                scenario = name.replace(" [speedup]", "")
                impl = "speedup"
            else:
                continue

            if scenario not in grouped:
                grouped[scenario] = {}
            grouped[scenario][impl] = result
        return grouped

    grouped = group_results(results)

    print(f"{'Scenario':<30} {'marshmallow':<14} {'speedup_bytes':<14} {'speedup':<14} {'speedup vs mm':<14}")
    print("-" * 86)

    for scenario in sorted(grouped.keys()):
        ops = grouped[scenario]
        mm_time = ops.get("marshmallow", {}).get("avg_time", 0) * 1000
        sb_time = ops.get("speedup_bytes", {}).get("avg_time", 0) * 1000
        sp_time = ops.get("speedup", {}).get("avg_time", 0) * 1000

        speedup = mm_time / sp_time if sp_time > 0 else 0

        print(f"{scenario:<30} {mm_time:<14.3f} {sb_time:<14.3f} {sp_time:<14.3f} {speedup:.1f}x")

    print()


if __name__ == "__main__":
    run_benchmarks()
