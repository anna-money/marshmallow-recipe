# Bytes Type Support

marshmallow-recipe supports `bytes` fields with automatic base64 encoding/decoding.

## Basic Usage

```python
import dataclasses
import marshmallow_recipe as mr

@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Document:
    name: str
    content: bytes

doc = Document(name="test.bin", content=b"\x00\x01\x02\x03")

# Dump - bytes are encoded to base64 string
dumped = mr.dump(Document, doc)
# {"name": "test.bin", "content": "AAECAw=="}

# Load - base64 string is decoded back to bytes
loaded = mr.load(Document, {"name": "test.bin", "content": "AAECAw=="})
# Document(name="test.bin", content=b"\x00\x01\x02\x03")
```

## Optional Bytes

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptionalContent:
    data: bytes | None = None

dumped = mr.dump(OptionalContent, OptionalContent())
# {}

loaded = mr.load(OptionalContent, {})
# OptionalContent(data=None)
```

## With Validation

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class LimitedContent:
    data: bytes = dataclasses.field(metadata=mr.meta(validate=lambda x: len(x) <= 1024))
```

## JSON Schema

```python
schema = mr.json_schema(Document)
# bytes fields are represented as {"type": "string", "format": "byte"} (OpenAPI standard for base64)
```
