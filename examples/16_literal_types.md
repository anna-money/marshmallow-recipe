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
