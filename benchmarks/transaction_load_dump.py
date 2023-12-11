import cProfile
import dataclasses
import datetime
import decimal
import marshmallow_recipe as mr
import uuid

from typing import Annotated


@dataclasses.dataclass(frozen=True)
class Transaction:
    id: uuid.UUID
    created_at: datetime.datetime
    processed_at: datetime.datetime | None
    amount: decimal.Decimal = dataclasses.field(metadata=mr.decimal_metadata(places=4))
    transaction_amount: Annotated[decimal.Decimal, mr.decimal_metadata(places=4)]


transaction = Transaction(
    id=uuid.uuid4(),
    created_at=datetime.datetime.utcnow(),
    processed_at=None,
    amount=decimal.Decimal(42),
    transaction_amount=decimal.Decimal(42),
 )

# to warm up the lib caches
assert mr.load_many(Transaction, mr.dump_many([transaction] * 1024))

cProfile.run("mr.load_many(Transaction, mr.dump_many([transaction] * 1024))", sort='tottime')
