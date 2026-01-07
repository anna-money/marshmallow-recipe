"""
Honest benchmark comparing full serialization cycles (bytes → object → bytes).

Uses the same serializer implementations as tests/api/conftest.py:
- marshmallow: mr.dump() + json.dumps() / json.loads() + mr.load()
- nuked_bytes: mr.nuked.dump_to_bytes() / mr.nuked.load_from_bytes()
- nuked: mr.nuked.dump() + json.dumps() / json.loads() + mr.nuked.load()
"""

import dataclasses
import datetime
import decimal
import json
import timeit
import uuid

import marshmallow_recipe as mr


# Test dataclasses
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Simple:
    name: str
    age: int
    active: bool


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTypes:
    id: uuid.UUID
    amount: decimal.Decimal
    created_at: datetime.datetime
    date: datetime.date


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Address:
    street: str
    city: str
    zip_code: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Person:
    name: str
    age: int
    address: Address


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithCollections:
    tags: list[str]
    scores: dict[str, int]
    ids: set[int]


# Serializers (same as conftest.py)
def marshmallow_dump(cls: type, obj: object) -> bytes:
    return json.dumps(mr.dump(cls, obj), separators=(",", ":")).encode()


def marshmallow_load[T](cls: type[T], data: bytes) -> T:
    return mr.load(cls, json.loads(data))


def nuked_bytes_dump(cls: type, obj: object) -> bytes:
    return mr.nuked.dump_to_bytes(cls, obj)


def nuked_bytes_load[T](cls: type[T], data: bytes) -> T:
    return mr.nuked.load_from_bytes(cls, data)


def nuked_dump(cls: type, obj: object) -> bytes:
    return json.dumps(mr.nuked.dump(cls, obj), separators=(",", ":")).encode()


def nuked_load[T](cls: type[T], data: bytes) -> T:
    return mr.nuked.load(cls, json.loads(data))


def benchmark(name: str, cls: type, obj: object, iterations: int = 10000) -> None:
    # Prepare data
    data = marshmallow_dump(cls, obj)

    # Warmup
    for _ in range(100):
        marshmallow_dump(cls, obj)
        marshmallow_load(cls, data)
        nuked_bytes_dump(cls, obj)
        nuked_bytes_load(cls, data)
        nuked_dump(cls, obj)
        nuked_load(cls, data)

    print(f"\n{'=' * 60}")
    print(f"{name} ({iterations} iterations)")
    print(f"{'=' * 60}")

    # Dump benchmarks
    t_mm_dump = timeit.timeit(lambda: marshmallow_dump(cls, obj), number=iterations)
    t_nuked_bytes_dump = timeit.timeit(lambda: nuked_bytes_dump(cls, obj), number=iterations)
    t_nuked_dump = timeit.timeit(lambda: nuked_dump(cls, obj), number=iterations)

    print(f"\nDump (object → bytes):")
    print(f"  marshmallow:  {t_mm_dump * 1000:.2f} ms")
    print(f"  nuked_bytes:  {t_nuked_bytes_dump * 1000:.2f} ms  ({t_mm_dump / t_nuked_bytes_dump:.1f}x faster)")
    print(f"  nuked:        {t_nuked_dump * 1000:.2f} ms  ({t_mm_dump / t_nuked_dump:.1f}x faster)")

    # Load benchmarks
    t_mm_load = timeit.timeit(lambda: marshmallow_load(cls, data), number=iterations)
    t_nuked_bytes_load = timeit.timeit(lambda: nuked_bytes_load(cls, data), number=iterations)
    t_nuked_load = timeit.timeit(lambda: nuked_load(cls, data), number=iterations)

    print(f"\nLoad (bytes → object):")
    print(f"  marshmallow:  {t_mm_load * 1000:.2f} ms")
    print(f"  nuked_bytes:  {t_nuked_bytes_load * 1000:.2f} ms  ({t_mm_load / t_nuked_bytes_load:.1f}x faster)")
    print(f"  nuked:        {t_nuked_load * 1000:.2f} ms  ({t_mm_load / t_nuked_load:.1f}x faster)")

    # Roundtrip
    t_mm_rt = timeit.timeit(lambda: marshmallow_load(cls, marshmallow_dump(cls, obj)), number=iterations)
    t_nuked_bytes_rt = timeit.timeit(lambda: nuked_bytes_load(cls, nuked_bytes_dump(cls, obj)), number=iterations)
    t_nuked_rt = timeit.timeit(lambda: nuked_load(cls, nuked_dump(cls, obj)), number=iterations)

    print(f"\nRoundtrip (object → bytes → object):")
    print(f"  marshmallow:  {t_mm_rt * 1000:.2f} ms")
    print(f"  nuked_bytes:  {t_nuked_bytes_rt * 1000:.2f} ms  ({t_mm_rt / t_nuked_bytes_rt:.1f}x faster)")
    print(f"  nuked:        {t_nuked_rt * 1000:.2f} ms  ({t_mm_rt / t_nuked_rt:.1f}x faster)")


def main() -> None:
    print("Honest Benchmark: Full Serialization Cycles")
    print("Same implementations as tests/api/conftest.py serializers")

    benchmark(
        "Simple (3 fields: str, int, bool)",
        Simple,
        Simple(name="John", age=30, active=True),
    )

    benchmark(
        "WithTypes (uuid, decimal, datetime, date)",
        WithTypes,
        WithTypes(
            id=uuid.uuid4(),
            amount=decimal.Decimal("123.45"),
            created_at=datetime.datetime.now(),
            date=datetime.date.today(),
        ),
    )

    benchmark(
        "Nested (Person with Address)",
        Person,
        Person(name="John", age=30, address=Address(street="123 Main St", city="Boston", zip_code="02101")),
    )

    benchmark(
        "Collections (list, dict, set)",
        WithCollections,
        WithCollections(
            tags=["python", "rust", "benchmark"],
            scores={"a": 1, "b": 2, "c": 3},
            ids={1, 2, 3, 4, 5},
        ),
    )


if __name__ == "__main__":
    main()
