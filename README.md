# marshmallow-recipe

The main goal of this opinionated library is to simplify migration from marshmallow2 to marshmallow3. 
Also, it helps with:
1. Stop writing marshmallow schemas completely: it generates them from dataclass. 
2. Using different naming cases(camel and capital camel cases are supported).
3. Utilizing best practises on fields configuration.


```python
import dataclasses
import datetime
import decimal
import marshmallow_recipe as mr
import uuid

@dataclasses.dataclass(frozen=True)
class Transaction:
    id: uuid.UUID
    created_at: datetime.datetime
    processed_at: datetime.datetime | None
    amount: decimal.Decimal

transaction = Transaction(
    id=uuid.uuid4(),
    created_at=datetime.datetime.utcnow(),
    processed_at=None,
    amount=decimal.Decimal(42),
 )

# dumps the transaction to a dict
raw = mr.dump(transaction) 

# loads a transaction from the dict
mr.load(Transaction, raw)

# provides a generated marshmallow schema for dataclass
mr.schema(Transaction)
```

Update API example:

```python
import decimal
import dataclasses
import marshmallow_recipe as mr

@dataclasses.dataclass(frozen=True)
@mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
class CompanyUpdateData:
    name: str = mr.MISSING
    annual_turnover: decimal.Decimal | None = mr.MISSING

company_update_data = CompanyUpdateData(name="updated name")
dumped = mr.dump(company_update_data)
assert dumped == {"name": "updated name"}  # Note: no "annual_turnover" here

loaded = mr.load(CompanyUpdateData, {"name": "updated name"})
assert loaded.name == "updated name"
assert loaded.annual_turnover is mr.MISSING

loaded = mr.load(CompanyUpdateData, {"annual_turnover": None})
assert loaded.name is mr.MISSING
assert loaded.annual_turnover is None
```