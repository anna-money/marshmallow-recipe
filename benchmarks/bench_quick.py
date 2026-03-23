#!/usr/bin/env python3
import dataclasses
import datetime
import decimal
import enum
import time
import uuid
from typing import Annotated

import marshmallow_recipe as mr


class TransactionStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    DECLINED = "declined"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TransactionTransferDetails:
    account_name: str | None = None
    sort_code: str | None = None
    account_number: str | None = None
    account_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    iban: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TransactionPaymentInfo:
    transfer_details: TransactionTransferDetails
    end_to_end_id: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TransactionData:
    id: uuid.UUID
    status: TransactionStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
    amount: decimal.Decimal
    currency: str
    transaction_amount: decimal.Decimal
    transaction_currency: str
    description: str
    type: str
    account_id: uuid.UUID
    company_id: uuid.UUID
    processed_at: datetime.datetime | None = None
    card_id: uuid.UUID | None = None
    reference: str | None = None
    payment_info: TransactionPaymentInfo | None = None
    is_technical: bool = False


TRANSACTION = TransactionData(
    id=uuid.uuid4(),
    status=TransactionStatus.PROCESSED,
    created_at=datetime.datetime.now(tz=datetime.UTC),
    updated_at=datetime.datetime.now(tz=datetime.UTC),
    amount=decimal.Decimal("123.45"),
    currency="GBP",
    transaction_amount=decimal.Decimal("123.45"),
    transaction_currency="GBP",
    description="Payment to ACME Corp",
    type="FP",
    account_id=uuid.uuid4(),
    company_id=uuid.uuid4(),
    processed_at=datetime.datetime.now(tz=datetime.UTC),
    reference="REF123456",
    payment_info=TransactionPaymentInfo(
        transfer_details=TransactionTransferDetails(
            account_name="ACME Corp",
            sort_code="123456",
            account_number="12345678",
            account_id=uuid.uuid4(),
            company_id=uuid.uuid4(),
        ),
        end_to_end_id="E2E123",
    ),
)

DATA_DICT = mr.nuked.dump(TransactionData, TRANSACTION)

TRANSACTIONS_100 = [
    TransactionData(
        id=uuid.uuid4(),
        status=TransactionStatus.PROCESSED,
        created_at=datetime.datetime.now(tz=datetime.UTC),
        updated_at=datetime.datetime.now(tz=datetime.UTC),
        amount=decimal.Decimal("123.45"),
        currency="GBP",
        transaction_amount=decimal.Decimal("123.45"),
        transaction_currency="GBP",
        description=f"Payment {i}",
        type="FP",
        account_id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        reference=f"REF{i:06d}",
    )
    for i in range(100)
]

DATA_MANY_DICT = mr.nuked.dump(list[TransactionData], TRANSACTIONS_100)

import json

DATA_BYTES = json.dumps(DATA_DICT).encode()
DATA_MANY_BYTES = json.dumps(DATA_MANY_DICT).encode()


def bench(name, func, iterations=10000):
    func()
    start = time.perf_counter()
    for _ in range(iterations):
        func()
    elapsed = time.perf_counter() - start
    per_call_us = elapsed / iterations * 1_000_000
    print(f"{name:50s} {per_call_us:10.2f} us/call  ({iterations} iterations)")
    return per_call_us


print("=" * 75)
print("BASELINE: nuked dump/load (dict-based)")
print("=" * 75)

bench("nuked dump (single)", lambda: mr.nuked.dump(TransactionData, TRANSACTION))
bench("nuked load (single)", lambda: mr.nuked.load(TransactionData, DATA_DICT))
bench("nuked dump (100 items)", lambda: mr.nuked.dump(list[TransactionData], TRANSACTIONS_100), 1000)
bench("nuked load (100 items)", lambda: mr.nuked.load(list[TransactionData], DATA_MANY_DICT), 1000)

print()
print("=" * 75)
print("BASELINE: nuked dump + json.dumps / json.loads + nuked load")
print("=" * 75)

bench("nuked dump + json.dumps (single)", lambda: json.dumps(mr.nuked.dump(TransactionData, TRANSACTION)).encode())
bench("json.loads + nuked load (single)", lambda: mr.nuked.load(TransactionData, json.loads(DATA_BYTES)))
bench("nuked dump + json.dumps (100)", lambda: json.dumps(mr.nuked.dump(list[TransactionData], TRANSACTIONS_100)).encode(), 1000)
bench("json.loads + nuked load (100)", lambda: mr.nuked.load(list[TransactionData], json.loads(DATA_MANY_BYTES)), 1000)

print()
print("=" * 75)
print("REFERENCE: pure json.dumps/json.loads overhead")
print("=" * 75)
bench("json.dumps (single dict)", lambda: json.dumps(DATA_DICT).encode())
bench("json.loads (single bytes)", lambda: json.loads(DATA_BYTES))
bench("json.dumps (100 dicts)", lambda: json.dumps(DATA_MANY_DICT).encode(), 1000)
bench("json.loads (100 bytes)", lambda: json.loads(DATA_MANY_BYTES), 1000)

print()
print("=" * 75)
print("COMPARISON: marshmallow dump/load")
print("=" * 75)
bench("marshmallow dump (single)", lambda: mr.dump(TransactionData, TRANSACTION))
bench("marshmallow load (single)", lambda: mr.load(TransactionData, DATA_DICT))
bench("marshmallow dump (100 items)", lambda: mr.dump_many(TransactionData, TRANSACTIONS_100), 1000)
bench("marshmallow load (100 items)", lambda: mr.load_many(TransactionData, DATA_MANY_DICT), 1000)

if hasattr(mr.nuked, 'dump_to_bytes'):
    print()
    print("=" * 75)
    print("NEW: dump_to_bytes")
    print("=" * 75)
    bench("dump_to_bytes (single)", lambda: mr.nuked.dump_to_bytes(TransactionData, TRANSACTION))
    bench("dump_to_bytes (100 items)", lambda: mr.nuked.dump_to_bytes(list[TransactionData], TRANSACTIONS_100), 1000)

if hasattr(mr.nuked, 'load_from_bytes'):
    print()
    print("=" * 75)
    print("NEW: load_from_bytes")
    print("=" * 75)
    bench("load_from_bytes (single)", lambda: mr.nuked.load_from_bytes(TransactionData, DATA_BYTES))
    bench("load_from_bytes (100 items)", lambda: mr.nuked.load_from_bytes(list[TransactionData], DATA_MANY_BYTES), 1000)
