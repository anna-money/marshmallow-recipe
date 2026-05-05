# Literal Types

Support for `typing.Literal` to restrict field values to specific constants.

## String Literals

```python
import dataclasses
from typing import Literal

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Message:
    role: Literal["user", "assistant", "system"]
    content: str


obj = Message(role="user", content="Hello")
data = mr.dump(Message, obj)
# b'{"content":"Hello","role":"user"}'

loaded = mr.load(Message, data)
# Message(role='user', content='Hello')
```

## Integer Literals

```python
import dataclasses
from typing import Literal

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class HttpResponse:
    status: Literal[200, 404, 500]
    body: str


obj = HttpResponse(status=200, body="OK")
data = mr.dump(HttpResponse, obj)
# b'{"body":"OK","status":200}'

loaded = mr.load(HttpResponse, data)
# HttpResponse(status=200, body='OK')
```

## Boolean Literals

```python
import dataclasses
from typing import Literal

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FeatureFlag:
    name: str
    enabled: Literal[True]


obj = FeatureFlag(name="dark_mode", enabled=True)
data = mr.dump(FeatureFlag, obj)
# b'{"enabled":true,"name":"dark_mode"}'

loaded = mr.load(FeatureFlag, data)
# FeatureFlag(name='dark_mode', enabled=True)
```

## Optional Literals

```python
import dataclasses
from typing import Literal

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Config:
    mode: Literal["fast", "slow"] | None = None
    priority: Literal[1, 2, 3] | None = None
    verbose: Literal[True, False] | None = None


obj = Config()
data = mr.dump(Config, obj)
# b'{}'

obj = Config(mode="fast", priority=1, verbose=True)
data = mr.dump(Config, obj)
# b'{"mode":"fast","priority":1,"verbose":true}'
```

## Literals with MISSING

```python
import dataclasses
from typing import Literal

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PatchRequest:
    priority: Literal["low", "medium", "high"] = mr.MISSING


obj = PatchRequest()
data = mr.dump(PatchRequest, obj)
# b'{}'

obj = PatchRequest(priority="high")
data = mr.dump(PatchRequest, obj)
# b'{"priority":"high"}'
```

## Validation

Invalid values raise `ValidationError`:

```python
import marshmallow_recipe as mr

# Loading invalid value raises ValidationError:
# {"role": ["Not a valid value. Allowed values: ['user', 'assistant', 'system']"]}
```

## Enum Member Literals

`Literal[<enum member>, ...]` constrains a field to a specific subset of an
`enum.StrEnum` or `enum.IntEnum`. Load returns the enum member; dump emits
the member's `.value`. All members in a single `Literal[...]` must belong
to the same enum class.

```python
import dataclasses
import enum
from typing import Literal

import marshmallow_recipe as mr


class Status(enum.StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Subscription:
    status: Literal[Status.ACTIVE, Status.INACTIVE]


loaded = mr.load(Subscription, {"status": "active"})
# Subscription(status=<Status.ACTIVE: 'active'>)
# loaded.status is Status.ACTIVE  # True

data = mr.dump(Subscription, loaded)
# {"status": "active"}

# A member of the enum that is NOT in the literal subset is rejected
# on both load and dump:
# mr.load(Subscription, {"status": "pending"})
# → ValidationError: {"status": ["Not a valid value. Allowed values: ['active', 'inactive']"]}
```

### IntEnum

```python
class HttpStatus(enum.IntEnum):
    OK = 200
    NOT_FOUND = 404
    INTERNAL_ERROR = 500


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Response:
    status: Literal[HttpStatus.OK, HttpStatus.NOT_FOUND]


loaded = mr.load(Response, {"status": 200})
# loaded.status is HttpStatus.OK  # True
```

### Discriminated Unions

Pair `Literal[<enum member>]` fields with a union of dataclasses to
implement discriminated unions:

```python
class Kind(enum.StrEnum):
    DOG = "DOG"
    CAT = "CAT"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Dog:
    kind: Literal[Kind.DOG]
    age: int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Cat:
    kind: Literal[Kind.CAT]
    name: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Pet:
    animal: Dog | Cat


mr.load(Pet, {"animal": {"kind": "CAT", "name": "Whiskers"}})
# Pet(animal=Cat(kind=<Kind.CAT: 'CAT'>, name='Whiskers'))
```

`Literal[<enum>, "raw_str"]` (mixing enum members with primitives) and
`Literal[A.X, B.Y]` (mixing classes) raise `ValueError` at schema-build
time.
