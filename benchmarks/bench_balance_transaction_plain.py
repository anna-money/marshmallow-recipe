#!/usr/bin/env python3
"""
Benchmark marshmallow vs nuked serialization on realistic balance TransactionData.

Plain @dataclasses.dataclass version — no frozen, slots, kw_only.
Compare with bench_balance_transaction.py to measure the overhead of
dataclass parameters (frozen/slots/kw_only).
"""
import dataclasses
import datetime
import decimal
import enum
import uuid
from typing import Annotated

import pyperf

import marshmallow_recipe as mr


# ── Enums ──────────────────────────────────────────────────────────────────────


class TransactionStatus(enum.StrEnum):
    PENDING = "pending"
    DUE = "due"
    PROCESSED = "processed"
    CANCELED = "canceled"
    DECLINED = "declined"
    DELETED = "deleted"


class TransactionDirection(enum.StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class TransactionFxFixedSide(enum.StrEnum):
    FROM = "FROM"
    TO = "TO"


class AccountFeatureBlockStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CardBlockedStatus(enum.StrEnum):
    BLOCKED = "BLOCKED"
    UNBLOCKED = "UNBLOCKED"


# ── Nested dataclasses (leaf → root) ──────────────────────────────────────────


@dataclasses.dataclass
class TransactionTransferDetails:
    account_name: str | None = None
    bsb: str | None = None
    sort_code: str | None = None
    account_number: str | None = None
    account_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None
    bic_swift: str | None = None
    intermediary_bic_swift: str | None = None
    iban: str | None = None
    aba: str | None = None
    bank_country: str | None = None
    purpose_code: str | None = None
    country: str | None = None
    city: str | None = None
    postcode: str | None = None
    state_or_province: str | None = None
    address: str | None = None
    message: str | None = None


@dataclasses.dataclass
class TransactionPaymentTransportDetails:
    account_name: str | None = None
    transaction_id: str | None = None
    mt103: str | None = None
    pacs008: str | None = None


@dataclasses.dataclass
class TransactionAccountDetails:
    account_name: str | None = None
    bsb: str | None = None
    sort_code: str | None = None
    account_number: str | None = None
    bic_swift: str | None = None
    iban: str | None = None
    aba: str | None = None


@dataclasses.dataclass
class TransactionPaymentInfo:
    transfer_details: TransactionTransferDetails
    transport_details: TransactionPaymentTransportDetails
    account_details: TransactionAccountDetails | None = None


@dataclasses.dataclass
class TransactionReturnInfo:
    initial_transaction_id: uuid.UUID


@dataclasses.dataclass
class TransactionLinkedTransactionInfo:
    transaction_id: uuid.UUID | None = None
    account_id: uuid.UUID | None = None
    company_id: uuid.UUID | None = None


@dataclasses.dataclass
class TransactionPotTransferInfo:
    related_transaction_account_id: uuid.UUID | None = None
    related_transaction_id: uuid.UUID | None = None


@dataclasses.dataclass
class TransactionFxInfo:
    conversion_id: uuid.UUID | None = None
    rate: Annotated[decimal.Decimal | None, mr.decimal_meta(places=12, rounding=decimal.ROUND_DOWN)] = None
    fixed_side: TransactionFxFixedSide | None = None
    markup_percent: decimal.Decimal | None = None


@dataclasses.dataclass
class TransactionCashbackInfo:
    reason: str


@dataclasses.dataclass
class TransactionCashInfo:
    receipt_message: str | None = None
    store_address: str | None = None
    store_name: str | None = None


@dataclasses.dataclass
class TransactionDdInfo:
    due_date: datetime.date | None = None


@dataclasses.dataclass
class TransactionInterestInfo:
    period_start: datetime.date
    period_end: datetime.date


@dataclasses.dataclass
class TransactionMerchantInfo:
    category_code: str | None = None
    category_name: str | None = None
    id: str | None = None
    name: str | None = None
    country: str | None = None
    address: str | None = None
    group_id: uuid.UUID | None = None


@dataclasses.dataclass
class TransactionPosTerminalInfo:
    id: str | None = None


@dataclasses.dataclass
class TransactionAvsCheckInfo:
    status: str | None = None
    postcode: str | None = None
    address: str | None = None


@dataclasses.dataclass
class TransactionDisputeInfo:
    step: str
    disputed_transaction_id: uuid.UUID | None = None


@dataclasses.dataclass
class TransactionPaymentTokenLifecycleInfo:
    phase: str
    device_id: str | None = None
    device_ip: str | None = None
    device_name: str | None = None
    device_phone_number: str | None = None
    wallet_type: str | None = None


@dataclasses.dataclass
class TransactionCardTransactionInfo:
    card_id: uuid.UUID
    alias: str
    card_chain_id: uuid.UUID
    merchant_info: TransactionMerchantInfo | None = None
    pos_terminal_info: TransactionPosTerminalInfo | None = None
    is_contactless: bool = False
    payment_token_id: uuid.UUID | None = None
    payment_token_wallet_type: str | None = None
    avs_check_result: str | None = None
    avs_check: TransactionAvsCheckInfo | None = None
    is_canceled_by_merchant: bool = False
    dispute_info: TransactionDisputeInfo | None = None
    payment_token_lifecycle_info: TransactionPaymentTokenLifecycleInfo | None = None
    auth_code: str | None = None
    retrieval_reference: str | None = None


@dataclasses.dataclass
class AccountFeatureBlock:
    feature: str
    actor: str
    status: AccountFeatureBlockStatus


@dataclasses.dataclass
class TransactionDeclineBlockedAccountFeatureInfo:
    account_feature_blocks: list[AccountFeatureBlock]


@dataclasses.dataclass
class TransactionCardBlockInfo:
    blocked_status: CardBlockedStatus | None = None
    blocked_by: str | None = None


@dataclasses.dataclass
class TransactionDeclineInfo:
    decline_reason: str | None = None
    blocked_account_feature: TransactionDeclineBlockedAccountFeatureInfo | None = None
    card_block_info: TransactionCardBlockInfo | None = None
    declined_by: str | None = None


@dataclasses.dataclass
class TransactionDeletionInfo:
    merged_into: uuid.UUID | None = None


LEGACY_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclasses.dataclass
class TransactionData:
    id: uuid.UUID
    status: TransactionStatus
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_metadata(format=LEGACY_DATETIME_FORMAT))
    updated_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_metadata(format=LEGACY_DATETIME_FORMAT))
    amount: decimal.Decimal
    currency: str
    transaction_amount: Annotated[decimal.Decimal, mr.decimal_meta(places=2, rounding=decimal.ROUND_HALF_UP)]
    transaction_currency: str
    description: str
    type: str
    account_id: uuid.UUID
    company_id: uuid.UUID
    processed_at: datetime.datetime | None = dataclasses.field(
        default=None, metadata=mr.datetime_metadata(format=LEGACY_DATETIME_FORMAT)
    )
    card_id: uuid.UUID | None = None
    alias: str | None = None
    reference: str | None = None
    external_entity_id: uuid.UUID | None = None
    decline_reason: str | None = None
    decline_info: TransactionDeclineInfo | None = None
    deletion_info: TransactionDeletionInfo | None = None
    payment_info: TransactionPaymentInfo | None = None
    return_info: TransactionReturnInfo | None = None
    linked_transaction_info: TransactionLinkedTransactionInfo | None = None
    pot_transfer_info: TransactionPotTransferInfo | None = None
    fx_info: TransactionFxInfo | None = None
    cashback_info: TransactionCashbackInfo | None = None
    cash_info: TransactionCashInfo | None = None
    dd_info: TransactionDdInfo | None = None
    interest_info: TransactionInterestInfo | None = None
    card_transaction_info: TransactionCardTransactionInfo | None = None
    is_technical: bool = False
    logo: str | None = None
    internal_reference: str | None = None


# ── Test data: realistic Faster Payment transaction ───────────────────────────


def _make_fp_transaction(i: int = 0) -> TransactionData:
    return TransactionData(
        id=uuid.uuid4(),
        status=TransactionStatus.PROCESSED,
        created_at=datetime.datetime(2024, 6, 15, 10, 30, 0, tzinfo=datetime.UTC),
        updated_at=datetime.datetime(2024, 6, 15, 10, 30, 5, tzinfo=datetime.UTC),
        amount=decimal.Decimal("1250.00"),
        currency="GBP",
        transaction_amount=decimal.Decimal("1250.00"),
        transaction_currency="GBP",
        description=f"Faster Payment to ACME Corp {i}",
        type="FP",
        account_id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        processed_at=datetime.datetime(2024, 6, 15, 10, 30, 5, tzinfo=datetime.UTC),
        alias="business-current",
        reference=f"INV-2024-{i:06d}",
        external_entity_id=uuid.uuid4(),
        payment_info=TransactionPaymentInfo(
            transfer_details=TransactionTransferDetails(
                account_name="ACME Corp Ltd",
                sort_code="040004",
                account_number="12345678",
                account_id=uuid.uuid4(),
                company_id=uuid.uuid4(),
                bank_country="GB",
                country="GB",
                city="London",
                postcode="EC1A 1BB",
                address="123 Business Road",
                message="Invoice payment INV-2024",
            ),
            transport_details=TransactionPaymentTransportDetails(
                account_name="ACME Corp Ltd",
                transaction_id="FP-TXN-20240615-001",
            ),
            account_details=TransactionAccountDetails(
                account_name="My Business Account",
                sort_code="040004",
                account_number="87654321",
            ),
        ),
        fx_info=TransactionFxInfo(
            conversion_id=uuid.uuid4(),
            rate=decimal.Decimal("1.000000000000"),
            fixed_side=TransactionFxFixedSide.FROM,
            markup_percent=decimal.Decimal("0.00"),
        ),
        linked_transaction_info=TransactionLinkedTransactionInfo(
            transaction_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            company_id=uuid.uuid4(),
        ),
        is_technical=False,
        logo="acme-corp",
        internal_reference="INT-REF-001",
    )


TRANSACTION = _make_fp_transaction()
TRANSACTIONS = [_make_fp_transaction(i) for i in range(100)]
TRANSACTIONS_1000 = [_make_fp_transaction(i) for i in range(1000)]


# ── Benchmark functions: single ───────────────────────────────────────────────


def marshmallow_dump() -> dict:
    return mr.dump(TransactionData, TRANSACTION)


def nuked_dump() -> dict:
    return mr.nuked.dump(TransactionData, TRANSACTION)


DATA_DICT = marshmallow_dump()


def marshmallow_load() -> TransactionData:
    return mr.load(TransactionData, DATA_DICT)


def nuked_load() -> TransactionData:
    return mr.nuked.load(TransactionData, DATA_DICT)


# ── Benchmark functions: 100 items ────────────────────────────────────────────


def marshmallow_dump_many() -> list[dict]:
    return mr.dump_many(TransactionData, TRANSACTIONS)


def nuked_dump_many() -> list[dict]:
    return mr.nuked.dump(list[TransactionData], TRANSACTIONS)


DATA_MANY_DICT = marshmallow_dump_many()


def marshmallow_load_many() -> list[TransactionData]:
    return mr.load_many(TransactionData, DATA_MANY_DICT)


def nuked_load_many() -> list[TransactionData]:
    return mr.nuked.load(list[TransactionData], DATA_MANY_DICT)


# ── Benchmark functions: 1000 items ───────────────────────────────────────────


def marshmallow_dump_many_1000() -> list[dict]:
    return mr.dump_many(TransactionData, TRANSACTIONS_1000)


def nuked_dump_many_1000() -> list[dict]:
    return mr.nuked.dump(list[TransactionData], TRANSACTIONS_1000)


DATA_MANY_1000_DICT = marshmallow_dump_many_1000()


def marshmallow_load_many_1000() -> list[TransactionData]:
    return mr.load_many(TransactionData, DATA_MANY_1000_DICT)


def nuked_load_many_1000() -> list[TransactionData]:
    return mr.nuked.load(list[TransactionData], DATA_MANY_1000_DICT)


# ── Runner ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    runner = pyperf.Runner()
    # Single item
    runner.bench_func("balance_marshmallow_dump", marshmallow_dump)
    runner.bench_func("balance_nuked_dump", nuked_dump)
    runner.bench_func("balance_marshmallow_load", marshmallow_load)
    runner.bench_func("balance_nuked_load", nuked_load)
    # 100 items
    runner.bench_func("balance_marshmallow_dump_many", marshmallow_dump_many)
    runner.bench_func("balance_nuked_dump_many", nuked_dump_many)
    runner.bench_func("balance_marshmallow_load_many", marshmallow_load_many)
    runner.bench_func("balance_nuked_load_many", nuked_load_many)
    # 1000 items
    runner.bench_func("balance_marshmallow_dump_many_1000", marshmallow_dump_many_1000)
    runner.bench_func("balance_nuked_dump_many_1000", nuked_dump_many_1000)
    runner.bench_func("balance_marshmallow_load_many_1000", marshmallow_load_many_1000)
    runner.bench_func("balance_nuked_load_many_1000", nuked_load_many_1000)
