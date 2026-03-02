# PEP 695 Type Aliases

Support for PEP 695 `type` statement aliases (`TypeAliasType`). Type aliases are unwrapped transparently everywhere: field types, `dump`/`load`/`dump_many`/`load_many`, `nuked`, and `json_schema`.

## As Field Types

```python
import dataclasses

import marshmallow_recipe as mr

type UserName = str

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    name: UserName


obj = User(name="Alice")
data = mr.dump(User, obj)
# {"name": "Alice"}

loaded = mr.load(User, data)
# User(name='Alice')
```

## Discriminated Union (dump/load/dump_many/load_many)

```python
import dataclasses
from typing import Literal

import marshmallow_recipe as mr

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UserMessage:
    text: str
    role: Literal["user"] = "user"

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AssistantMessage:
    text: str
    role: Literal["assistant"] = "assistant"

type Message = UserMessage | AssistantMessage

mr.dump(Message, UserMessage(text="hi"))
# {"text": "hi", "role": "user"}

mr.load(Message, {"text": "hello", "role": "assistant"})
# AssistantMessage(text='hello', role='assistant')

messages = [UserMessage(text="hi"), AssistantMessage(text="hello")]
mr.dump_many(Message, messages)
# [{"text": "hi", "role": "user"}, {"text": "hello", "role": "assistant"}]

mr.load_many(Message, [{"text": "hi", "role": "user"}, {"text": "hello", "role": "assistant"}])
# [UserMessage(text='hi', role='user'), AssistantMessage(text='hello', role='assistant')]
```

## Nuked

```python
import marshmallow_recipe as mr

mr.nuked.dump(Message, UserMessage(text="hi"))
# {"text": "hi", "role": "user"}

mr.nuked.load(Message, {"text": "hello", "role": "assistant"})
# AssistantMessage(text='hello', role='assistant')

mr.nuked.dump(list[Message], [UserMessage(text="hi"), AssistantMessage(text="hello")])
# [{"text": "hi", "role": "user"}, {"text": "hello", "role": "assistant"}]

mr.nuked.load(list[Message], [{"text": "hi", "role": "user"}, {"text": "hello", "role": "assistant"}])
# [UserMessage(text='hi', role='user'), AssistantMessage(text='hello', role='assistant')]
```

## As Fields in Dataclasses

```python
import dataclasses

import marshmallow_recipe as mr

type OptionalStr = str | None

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Config:
    value: OptionalStr = None


mr.dump(Config, Config())
# {}

mr.dump(Config, Config(value="hello"))
# {"value": "hello"}
```
