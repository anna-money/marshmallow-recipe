import marshmallow_recipe as mr


def test_metadata_different_keys_order() -> None:
    metadata1 = mr.Metadata({"a": 1, "b": 2})
    metadata2 = mr.Metadata({"b": 2, "a": 1})

    assert hash(metadata1) == hash(metadata2)
    assert metadata1 == metadata2


def test_metadata_not_equal_same_hash() -> None:
    metadata1 = mr.Metadata({"a": 1, "b": 1})
    metadata2 = mr.Metadata({"b": 2, "a": 2})

    assert hash(metadata1) == hash(metadata2)
    assert metadata1 != metadata2


def test_metadata_not_equal() -> None:
    metadata1 = mr.Metadata({"a": 1, "b": 1})
    metadata2 = mr.Metadata({"b": 2, "c": 2})

    assert hash(metadata1) != hash(metadata2)
    assert metadata1 != metadata2
