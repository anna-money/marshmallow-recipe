#!/usr/bin/env python3
"""
Benchmark marshmallow vs nuked serialization.

Based on real-world TransactionData model from anna-balance.
"""
import dataclasses
import datetime
import decimal
import enum
import json
import uuid

import pyperf

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
class TransactionMerchantInfo:
    category_code: str | None = None
    name: str | None = None
    country: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TransactionCardTransactionInfo:
    merchant_info: TransactionMerchantInfo | None = None
    auth_code: str | None = None


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
    card_transaction_info: TransactionCardTransactionInfo | None = None
    is_technical: bool = False


# Test data
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


def marshmallow_dump() -> bytes:
    return json.dumps(mr.dump(TransactionData, TRANSACTION), separators=(",", ":")).encode()


def nuked_dump() -> bytes:
    return json.dumps(mr.nuked.dump(TransactionData, TRANSACTION), separators=(",", ":")).encode()


def nuked_dump_to_bytes() -> bytes:
    return mr.nuked.dump_to_bytes(TransactionData, TRANSACTION)


DATA = marshmallow_dump()
DATA_DICT = json.loads(DATA)

# List of 100 transactions
TRANSACTIONS = [
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


def marshmallow_dump_many() -> bytes:
    return json.dumps(mr.dump_many(TransactionData, TRANSACTIONS), separators=(",", ":")).encode()


def nuked_dump_many() -> bytes:
    return json.dumps(mr.nuked.dump(list[TransactionData], TRANSACTIONS), separators=(",", ":")).encode()


def nuked_dump_to_bytes_many() -> bytes:
    return mr.nuked.dump_to_bytes(list[TransactionData], TRANSACTIONS)


DATA_MANY = marshmallow_dump_many()


def marshmallow_load_many() -> list[TransactionData]:
    return mr.load_many(TransactionData, json.loads(DATA_MANY))


def nuked_load_many() -> list[TransactionData]:
    return mr.nuked.load(list[TransactionData], json.loads(DATA_MANY))


def nuked_load_from_bytes_many() -> list[TransactionData]:
    return mr.nuked.load_from_bytes(list[TransactionData], DATA_MANY)


def marshmallow_load() -> TransactionData:
    return mr.load(TransactionData, json.loads(DATA))


def nuked_load() -> TransactionData:
    return mr.nuked.load(TransactionData, json.loads(DATA))


def nuked_load_from_bytes() -> TransactionData:
    return mr.nuked.load_from_bytes(TransactionData, DATA)


if __name__ == "__main__":
    runner = pyperf.Runner()
    # Single item
    runner.bench_func("marshmallow_dump", marshmallow_dump)
    runner.bench_func("nuked_dump", nuked_dump)
    runner.bench_func("nuked_dump_to_bytes", nuked_dump_to_bytes)
    runner.bench_func("marshmallow_load", marshmallow_load)
    runner.bench_func("nuked_load", nuked_load)
    runner.bench_func("nuked_load_from_bytes", nuked_load_from_bytes)
    # 100 items
    runner.bench_func("marshmallow_dump_many", marshmallow_dump_many)
    runner.bench_func("nuked_dump_many", nuked_dump_many)
    runner.bench_func("nuked_dump_to_bytes_many", nuked_dump_to_bytes_many)
    runner.bench_func("marshmallow_load_many", marshmallow_load_many)
    runner.bench_func("nuked_load_many", nuked_load_many)
    runner.bench_func("nuked_load_from_bytes_many", nuked_load_from_bytes_many)
