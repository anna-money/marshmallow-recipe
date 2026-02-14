#!/usr/bin/env python3
"""
Benchmark marshmallow vs nuked serialization.

Based on real-world TransactionData model from anna-balance.
"""
import dataclasses
import datetime
import decimal
import enum
import uuid
from typing import Annotated

import pyperf

import marshmallow_recipe as mr


class TransactionStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    DECLINED = "declined"


# Datetime-specific benchmarks to measure UTC optimization impact
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DatetimeOnlyUTC:
    dt1: datetime.datetime
    dt2: datetime.datetime
    dt3: datetime.datetime
    dt4: datetime.datetime
    dt5: datetime.datetime


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DatetimeOnlyNonUTC:
    dt1: datetime.datetime
    dt2: datetime.datetime
    dt3: datetime.datetime
    dt4: datetime.datetime
    dt5: datetime.datetime


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DictData:
    values: dict[str, str]


DICT_DATA = DictData(values={f"key_{i}": f"value_{i}" for i in range(50)})


def nuked_dump_dict() -> dict:
    return mr.nuked.dump(DictData, DICT_DATA)


DICT_DATA_DICT = nuked_dump_dict()


def nuked_load_dict() -> DictData:
    return mr.nuked.load(DictData, DICT_DATA_DICT)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ListIntData:
    values: list[int]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ListStrData:
    values: list[str]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ListIntData500:
    values: list[int]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ListStrData500:
    values: list[str]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DecimalLambdaValidated:
    d1: Annotated[decimal.Decimal, mr.meta(validate=lambda x: x > 0)]
    d2: Annotated[decimal.Decimal, mr.meta(validate=lambda x: x > 0)]
    d3: Annotated[decimal.Decimal, mr.meta(validate=lambda x: x > 0)]
    d4: Annotated[decimal.Decimal, mr.meta(validate=lambda x: x > 0)]
    d5: Annotated[decimal.Decimal, mr.meta(validate=lambda x: x > 0)]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DecimalRangeValidated:
    d1: Annotated[decimal.Decimal, mr.decimal_meta(gt=decimal.Decimal("0"))]
    d2: Annotated[decimal.Decimal, mr.decimal_meta(gt=decimal.Decimal("0"))]
    d3: Annotated[decimal.Decimal, mr.decimal_meta(gt=decimal.Decimal("0"))]
    d4: Annotated[decimal.Decimal, mr.decimal_meta(gt=decimal.Decimal("0"))]
    d5: Annotated[decimal.Decimal, mr.decimal_meta(gt=decimal.Decimal("0"))]


LIST_INT_DATA = ListIntData(values=list(range(50)))
LIST_STR_DATA = ListStrData(values=[f"value_{i}" for i in range(50)])
LIST_INT_DATA_500 = ListIntData500(values=list(range(500)))
LIST_STR_DATA_500 = ListStrData500(values=[f"value_{i}" for i in range(500)])


def nuked_dump_list_int() -> dict:
    return mr.nuked.dump(ListIntData, LIST_INT_DATA)


def nuked_dump_list_str() -> dict:
    return mr.nuked.dump(ListStrData, LIST_STR_DATA)


def nuked_dump_list_int_500() -> dict:
    return mr.nuked.dump(ListIntData500, LIST_INT_DATA_500)


def nuked_dump_list_str_500() -> dict:
    return mr.nuked.dump(ListStrData500, LIST_STR_DATA_500)


LIST_INT_DATA_DICT = nuked_dump_list_int()
LIST_STR_DATA_DICT = nuked_dump_list_str()
LIST_INT_DATA_500_DICT = nuked_dump_list_int_500()
LIST_STR_DATA_500_DICT = nuked_dump_list_str_500()


def nuked_load_list_int() -> ListIntData:
    return mr.nuked.load(ListIntData, LIST_INT_DATA_DICT)


def nuked_load_list_str() -> ListStrData:
    return mr.nuked.load(ListStrData, LIST_STR_DATA_DICT)


def nuked_load_list_int_500() -> ListIntData500:
    return mr.nuked.load(ListIntData500, LIST_INT_DATA_500_DICT)


def nuked_load_list_str_500() -> ListStrData500:
    return mr.nuked.load(ListStrData500, LIST_STR_DATA_500_DICT)


DECIMAL_LAMBDA = DecimalLambdaValidated(
    d1=decimal.Decimal("10.00"), d2=decimal.Decimal("20.00"),
    d3=decimal.Decimal("30.00"), d4=decimal.Decimal("40.00"),
    d5=decimal.Decimal("50.00"),
)
DECIMAL_RANGE = DecimalRangeValidated(
    d1=decimal.Decimal("10.00"), d2=decimal.Decimal("20.00"),
    d3=decimal.Decimal("30.00"), d4=decimal.Decimal("40.00"),
    d5=decimal.Decimal("50.00"),
)


def marshmallow_dump_decimal_lambda() -> dict:
    return mr.dump(DecimalLambdaValidated, DECIMAL_LAMBDA)


def nuked_dump_decimal_lambda() -> dict:
    return mr.nuked.dump(DecimalLambdaValidated, DECIMAL_LAMBDA)


DECIMAL_LAMBDA_DICT = marshmallow_dump_decimal_lambda()
DECIMAL_RANGE_DICT = mr.dump(DecimalRangeValidated, DECIMAL_RANGE)


def marshmallow_load_decimal_lambda() -> DecimalLambdaValidated:
    return mr.load(DecimalLambdaValidated, DECIMAL_LAMBDA_DICT)


def nuked_load_decimal_lambda() -> DecimalLambdaValidated:
    return mr.nuked.load(DecimalLambdaValidated, DECIMAL_LAMBDA_DICT)


def marshmallow_dump_decimal_range() -> dict:
    return mr.dump(DecimalRangeValidated, DECIMAL_RANGE)


def nuked_dump_decimal_range() -> dict:
    return mr.nuked.dump(DecimalRangeValidated, DECIMAL_RANGE)


def marshmallow_load_decimal_range() -> DecimalRangeValidated:
    return mr.load(DecimalRangeValidated, DECIMAL_RANGE_DICT)


def nuked_load_decimal_range() -> DecimalRangeValidated:
    return mr.nuked.load(DecimalRangeValidated, DECIMAL_RANGE_DICT)


DECIMALS_LAMBDA = [DECIMAL_LAMBDA] * 100
DECIMALS_RANGE = [DECIMAL_RANGE] * 100
DECIMALS_LAMBDA_1000 = [DECIMAL_LAMBDA] * 1000
DECIMALS_RANGE_1000 = [DECIMAL_RANGE] * 1000


def marshmallow_dump_many_decimal_lambda() -> list[dict]:
    return mr.dump_many(DecimalLambdaValidated, DECIMALS_LAMBDA)


def nuked_dump_many_decimal_lambda() -> list[dict]:
    return mr.nuked.dump(list[DecimalLambdaValidated], DECIMALS_LAMBDA)


def marshmallow_dump_many_decimal_range() -> list[dict]:
    return mr.dump_many(DecimalRangeValidated, DECIMALS_RANGE)


def nuked_dump_many_decimal_range() -> list[dict]:
    return mr.nuked.dump(list[DecimalRangeValidated], DECIMALS_RANGE)


DECIMALS_LAMBDA_MANY_DICT = marshmallow_dump_many_decimal_lambda()
DECIMALS_RANGE_MANY_DICT = marshmallow_dump_many_decimal_range()


def marshmallow_load_many_decimal_lambda() -> list[DecimalLambdaValidated]:
    return mr.load_many(DecimalLambdaValidated, DECIMALS_LAMBDA_MANY_DICT)


def nuked_load_many_decimal_lambda() -> list[DecimalLambdaValidated]:
    return mr.nuked.load(list[DecimalLambdaValidated], DECIMALS_LAMBDA_MANY_DICT)


def marshmallow_load_many_decimal_range() -> list[DecimalRangeValidated]:
    return mr.load_many(DecimalRangeValidated, DECIMALS_RANGE_MANY_DICT)


def nuked_load_many_decimal_range() -> list[DecimalRangeValidated]:
    return mr.nuked.load(list[DecimalRangeValidated], DECIMALS_RANGE_MANY_DICT)


def marshmallow_dump_many_1000_decimal_lambda() -> list[dict]:
    return mr.dump_many(DecimalLambdaValidated, DECIMALS_LAMBDA_1000)


def nuked_dump_many_1000_decimal_lambda() -> list[dict]:
    return mr.nuked.dump(list[DecimalLambdaValidated], DECIMALS_LAMBDA_1000)


def marshmallow_dump_many_1000_decimal_range() -> list[dict]:
    return mr.dump_many(DecimalRangeValidated, DECIMALS_RANGE_1000)


def nuked_dump_many_1000_decimal_range() -> list[dict]:
    return mr.nuked.dump(list[DecimalRangeValidated], DECIMALS_RANGE_1000)


DECIMALS_LAMBDA_MANY_1000_DICT = marshmallow_dump_many_1000_decimal_lambda()
DECIMALS_RANGE_MANY_1000_DICT = marshmallow_dump_many_1000_decimal_range()


def marshmallow_load_many_1000_decimal_lambda() -> list[DecimalLambdaValidated]:
    return mr.load_many(DecimalLambdaValidated, DECIMALS_LAMBDA_MANY_1000_DICT)


def nuked_load_many_1000_decimal_lambda() -> list[DecimalLambdaValidated]:
    return mr.nuked.load(list[DecimalLambdaValidated], DECIMALS_LAMBDA_MANY_1000_DICT)


def marshmallow_load_many_1000_decimal_range() -> list[DecimalRangeValidated]:
    return mr.load_many(DecimalRangeValidated, DECIMALS_RANGE_MANY_1000_DICT)


def nuked_load_many_1000_decimal_range() -> list[DecimalRangeValidated]:
    return mr.nuked.load(list[DecimalRangeValidated], DECIMALS_RANGE_MANY_1000_DICT)


FIXED_OFFSET = datetime.timezone(datetime.timedelta(hours=3))

DATETIME_UTC = DatetimeOnlyUTC(
    dt1=datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=datetime.UTC),
    dt2=datetime.datetime(2024, 2, 20, 14, 15, 30, tzinfo=datetime.UTC),
    dt3=datetime.datetime(2024, 3, 25, 8, 45, 0, tzinfo=datetime.UTC),
    dt4=datetime.datetime(2024, 4, 10, 16, 0, 15, tzinfo=datetime.UTC),
    dt5=datetime.datetime(2024, 5, 5, 12, 30, 0, tzinfo=datetime.UTC),
)

DATETIME_NON_UTC = DatetimeOnlyNonUTC(
    dt1=datetime.datetime(2024, 1, 15, 10, 30, 45, tzinfo=FIXED_OFFSET),
    dt2=datetime.datetime(2024, 2, 20, 14, 15, 30, tzinfo=FIXED_OFFSET),
    dt3=datetime.datetime(2024, 3, 25, 8, 45, 0, tzinfo=FIXED_OFFSET),
    dt4=datetime.datetime(2024, 4, 10, 16, 0, 15, tzinfo=FIXED_OFFSET),
    dt5=datetime.datetime(2024, 5, 5, 12, 30, 0, tzinfo=FIXED_OFFSET),
)


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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TransactionDataValidated:
    id: Annotated[uuid.UUID, mr.meta(validate=lambda x: True)]
    status: Annotated[TransactionStatus, mr.meta(validate=lambda x: True)]
    created_at: Annotated[datetime.datetime, mr.meta(validate=lambda x: True)]
    updated_at: Annotated[datetime.datetime, mr.meta(validate=lambda x: True)]
    amount: Annotated[decimal.Decimal, mr.meta(validate=lambda x: True)]
    currency: Annotated[str, mr.meta(validate=lambda x: True)]
    transaction_amount: Annotated[decimal.Decimal, mr.meta(validate=lambda x: True)]
    transaction_currency: Annotated[str, mr.meta(validate=lambda x: True)]
    description: Annotated[str, mr.meta(validate=lambda x: True)]
    type: Annotated[str, mr.meta(validate=lambda x: True)]
    account_id: Annotated[uuid.UUID, mr.meta(validate=lambda x: True)]
    company_id: Annotated[uuid.UUID, mr.meta(validate=lambda x: True)]
    processed_at: Annotated[datetime.datetime | None, mr.meta(validate=lambda x: True)] = None
    card_id: Annotated[uuid.UUID | None, mr.meta(validate=lambda x: True)] = None
    reference: Annotated[str | None, mr.meta(validate=lambda x: True)] = None
    is_technical: Annotated[bool, mr.meta(validate=lambda x: True)] = False


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


def marshmallow_dump() -> dict:
    return mr.dump(TransactionData, TRANSACTION)


def nuked_dump() -> dict:
    return mr.nuked.dump(TransactionData, TRANSACTION)


DATA_DICT = marshmallow_dump()

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

TRANSACTIONS_1000 = [
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
    for i in range(1000)
]


def marshmallow_dump_many() -> list[dict]:
    return mr.dump_many(TransactionData, TRANSACTIONS)


def nuked_dump_many() -> list[dict]:
    return mr.nuked.dump(list[TransactionData], TRANSACTIONS)


DATA_MANY_DICT = marshmallow_dump_many()


def marshmallow_load_many() -> list[TransactionData]:
    return mr.load_many(TransactionData, DATA_MANY_DICT)


def nuked_load_many() -> list[TransactionData]:
    return mr.nuked.load(list[TransactionData], DATA_MANY_DICT)


def marshmallow_dump_many_1000() -> list[dict]:
    return mr.dump_many(TransactionData, TRANSACTIONS_1000)


def nuked_dump_many_1000() -> list[dict]:
    return mr.nuked.dump(list[TransactionData], TRANSACTIONS_1000)


DATA_MANY_1000_DICT = marshmallow_dump_many_1000()


def marshmallow_load_many_1000() -> list[TransactionData]:
    return mr.load_many(TransactionData, DATA_MANY_1000_DICT)


def nuked_load_many_1000() -> list[TransactionData]:
    return mr.nuked.load(list[TransactionData], DATA_MANY_1000_DICT)


def marshmallow_load() -> TransactionData:
    return mr.load(TransactionData, DATA_DICT)


def nuked_load() -> TransactionData:
    return mr.nuked.load(TransactionData, DATA_DICT)


# Datetime-specific benchmark functions
def nuked_dump_datetime_utc() -> dict:
    return mr.nuked.dump(DatetimeOnlyUTC, DATETIME_UTC)


def nuked_dump_datetime_non_utc() -> dict:
    return mr.nuked.dump(DatetimeOnlyNonUTC, DATETIME_NON_UTC)


DATETIME_UTC_DATA = nuked_dump_datetime_utc()
DATETIME_NON_UTC_DATA = nuked_dump_datetime_non_utc()


def nuked_load_datetime_utc() -> DatetimeOnlyUTC:
    return mr.nuked.load(DatetimeOnlyUTC, DATETIME_UTC_DATA)


def nuked_load_datetime_non_utc() -> DatetimeOnlyNonUTC:
    return mr.nuked.load(DatetimeOnlyNonUTC, DATETIME_NON_UTC_DATA)


TRANSACTION_VALIDATED = TransactionDataValidated(
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
    reference="REF123456",
)

TRANSACTIONS_VALIDATED = [
    TransactionDataValidated(
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

TRANSACTIONS_VALIDATED_1000 = [
    TransactionDataValidated(
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
    for i in range(1000)
]


def marshmallow_dump_validated() -> dict:
    return mr.dump(TransactionDataValidated, TRANSACTION_VALIDATED)


def nuked_dump_validated() -> dict:
    return mr.nuked.dump(TransactionDataValidated, TRANSACTION_VALIDATED)


DATA_VALIDATED_DICT = marshmallow_dump_validated()


def marshmallow_load_validated() -> TransactionDataValidated:
    return mr.load(TransactionDataValidated, DATA_VALIDATED_DICT)


def nuked_load_validated() -> TransactionDataValidated:
    return mr.nuked.load(TransactionDataValidated, DATA_VALIDATED_DICT)


def marshmallow_dump_many_validated() -> list[dict]:
    return mr.dump_many(TransactionDataValidated, TRANSACTIONS_VALIDATED)


def nuked_dump_many_validated() -> list[dict]:
    return mr.nuked.dump(list[TransactionDataValidated], TRANSACTIONS_VALIDATED)


DATA_MANY_VALIDATED_DICT = marshmallow_dump_many_validated()


def marshmallow_load_many_validated() -> list[TransactionDataValidated]:
    return mr.load_many(TransactionDataValidated, DATA_MANY_VALIDATED_DICT)


def nuked_load_many_validated() -> list[TransactionDataValidated]:
    return mr.nuked.load(list[TransactionDataValidated], DATA_MANY_VALIDATED_DICT)


def marshmallow_dump_many_1000_validated() -> list[dict]:
    return mr.dump_many(TransactionDataValidated, TRANSACTIONS_VALIDATED_1000)


def nuked_dump_many_1000_validated() -> list[dict]:
    return mr.nuked.dump(list[TransactionDataValidated], TRANSACTIONS_VALIDATED_1000)


DATA_MANY_1000_VALIDATED_DICT = marshmallow_dump_many_1000_validated()


def marshmallow_load_many_1000_validated() -> list[TransactionDataValidated]:
    return mr.load_many(TransactionDataValidated, DATA_MANY_1000_VALIDATED_DICT)


def nuked_load_many_1000_validated() -> list[TransactionDataValidated]:
    return mr.nuked.load(list[TransactionDataValidated], DATA_MANY_1000_VALIDATED_DICT)


if __name__ == "__main__":
    runner = pyperf.Runner()
    # Single item
    runner.bench_func("marshmallow_dump", marshmallow_dump)
    runner.bench_func("nuked_dump", nuked_dump)
    runner.bench_func("marshmallow_load", marshmallow_load)
    runner.bench_func("nuked_load", nuked_load)
    # 100 items
    runner.bench_func("marshmallow_dump_many", marshmallow_dump_many)
    runner.bench_func("nuked_dump_many", nuked_dump_many)
    runner.bench_func("marshmallow_load_many", marshmallow_load_many)
    runner.bench_func("nuked_load_many", nuked_load_many)
    # 1000 items
    runner.bench_func("marshmallow_dump_many_1000", marshmallow_dump_many_1000)
    runner.bench_func("nuked_dump_many_1000", nuked_dump_many_1000)
    runner.bench_func("marshmallow_load_many_1000", marshmallow_load_many_1000)
    runner.bench_func("nuked_load_many_1000", nuked_load_many_1000)
    # Single item validated
    runner.bench_func("marshmallow_dump_validated", marshmallow_dump_validated)
    runner.bench_func("nuked_dump_validated", nuked_dump_validated)
    runner.bench_func("marshmallow_load_validated", marshmallow_load_validated)
    runner.bench_func("nuked_load_validated", nuked_load_validated)
    # 100 items validated
    runner.bench_func("marshmallow_dump_many_validated", marshmallow_dump_many_validated)
    runner.bench_func("nuked_dump_many_validated", nuked_dump_many_validated)
    runner.bench_func("marshmallow_load_many_validated", marshmallow_load_many_validated)
    runner.bench_func("nuked_load_many_validated", nuked_load_many_validated)
    # 1000 items validated
    runner.bench_func("marshmallow_dump_many_1000_validated", marshmallow_dump_many_1000_validated)
    runner.bench_func("nuked_dump_many_1000_validated", nuked_dump_many_1000_validated)
    runner.bench_func("marshmallow_load_many_1000_validated", marshmallow_load_many_1000_validated)
    runner.bench_func("nuked_load_many_1000_validated", nuked_load_many_1000_validated)
    # Datetime-specific (UTC vs non-UTC)
    runner.bench_func("nuked_dump_datetime_utc", nuked_dump_datetime_utc)
    runner.bench_func("nuked_dump_datetime_non_utc", nuked_dump_datetime_non_utc)
    runner.bench_func("nuked_load_datetime_utc", nuked_load_datetime_utc)
    runner.bench_func("nuked_load_datetime_non_utc", nuked_load_datetime_non_utc)
    # Dict field
    runner.bench_func("nuked_dump_dict", nuked_dump_dict)
    runner.bench_func("nuked_load_dict", nuked_load_dict)
    # List field
    runner.bench_func("nuked_dump_list_int", nuked_dump_list_int)
    runner.bench_func("nuked_load_list_int", nuked_load_list_int)
    runner.bench_func("nuked_dump_list_str", nuked_dump_list_str)
    runner.bench_func("nuked_load_list_str", nuked_load_list_str)
    runner.bench_func("nuked_dump_list_int_500", nuked_dump_list_int_500)
    runner.bench_func("nuked_load_list_int_500", nuked_load_list_int_500)
    runner.bench_func("nuked_dump_list_str_500", nuked_dump_list_str_500)
    runner.bench_func("nuked_load_list_str_500", nuked_load_list_str_500)
    # Decimal range validation: lambda vs native
    runner.bench_func("marshmallow_dump_decimal_lambda", marshmallow_dump_decimal_lambda)
    runner.bench_func("nuked_dump_decimal_lambda", nuked_dump_decimal_lambda)
    runner.bench_func("marshmallow_load_decimal_lambda", marshmallow_load_decimal_lambda)
    runner.bench_func("nuked_load_decimal_lambda", nuked_load_decimal_lambda)
    runner.bench_func("marshmallow_dump_decimal_range", marshmallow_dump_decimal_range)
    runner.bench_func("nuked_dump_decimal_range", nuked_dump_decimal_range)
    runner.bench_func("marshmallow_load_decimal_range", marshmallow_load_decimal_range)
    runner.bench_func("nuked_load_decimal_range", nuked_load_decimal_range)
    # Decimal range validation: 100 items
    runner.bench_func("marshmallow_dump_many_decimal_lambda", marshmallow_dump_many_decimal_lambda)
    runner.bench_func("nuked_dump_many_decimal_lambda", nuked_dump_many_decimal_lambda)
    runner.bench_func("marshmallow_load_many_decimal_lambda", marshmallow_load_many_decimal_lambda)
    runner.bench_func("nuked_load_many_decimal_lambda", nuked_load_many_decimal_lambda)
    runner.bench_func("marshmallow_dump_many_decimal_range", marshmallow_dump_many_decimal_range)
    runner.bench_func("nuked_dump_many_decimal_range", nuked_dump_many_decimal_range)
    runner.bench_func("marshmallow_load_many_decimal_range", marshmallow_load_many_decimal_range)
    runner.bench_func("nuked_load_many_decimal_range", nuked_load_many_decimal_range)
    # Decimal range validation: 1000 items
    runner.bench_func("marshmallow_dump_many_1000_decimal_lambda", marshmallow_dump_many_1000_decimal_lambda)
    runner.bench_func("nuked_dump_many_1000_decimal_lambda", nuked_dump_many_1000_decimal_lambda)
    runner.bench_func("marshmallow_load_many_1000_decimal_lambda", marshmallow_load_many_1000_decimal_lambda)
    runner.bench_func("nuked_load_many_1000_decimal_lambda", nuked_load_many_1000_decimal_lambda)
    runner.bench_func("marshmallow_dump_many_1000_decimal_range", marshmallow_dump_many_1000_decimal_range)
    runner.bench_func("nuked_dump_many_1000_decimal_range", nuked_dump_many_1000_decimal_range)
    runner.bench_func("marshmallow_load_many_1000_decimal_range", marshmallow_load_many_1000_decimal_range)
    runner.bench_func("nuked_load_many_1000_decimal_range", nuked_load_many_1000_decimal_range)
