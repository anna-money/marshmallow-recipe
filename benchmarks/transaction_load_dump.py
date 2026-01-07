import cProfile
import dataclasses
import datetime
import decimal
import uuid
from typing import Annotated

import marshmallow_recipe as mr
import marshmallow_recipe.speedup as mrs


@dataclasses.dataclass(frozen=True)
class Transaction:
    id: uuid.UUID
    created_at: datetime.datetime
    processed_at: datetime.datetime | None
    amount: decimal.Decimal = dataclasses.field(metadata=mr.decimal_metadata(places=4))
    transaction_amount: Annotated[decimal.Decimal, mr.decimal_metadata(places=4)]


transaction = Transaction(
    id=uuid.uuid4(),
    created_at=datetime.datetime.now(datetime.UTC),
    processed_at=None,
    amount=decimal.Decimal(42),
    transaction_amount=decimal.Decimal(42),
)

# to warm up the lib caches
assert mrs.load(list[Transaction], mrs.dump(list[Transaction], [transaction] * 1024))

cProfile.run("mrs.load(list[Transaction], mrs.dump(list[Transaction], [transaction] * 1024))", sort="tottime")
