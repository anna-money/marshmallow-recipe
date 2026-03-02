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
```

## Optional Literals

```python
import dataclasses
from typing import Literal

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Config:
    mode: Literal["fast", "slow"] | None = None


obj = Config()
data = mr.dump(Config, obj)
# b'{}'

obj = Config(mode="fast")
data = mr.dump(Config, obj)
# b'{"mode":"fast"}'
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
