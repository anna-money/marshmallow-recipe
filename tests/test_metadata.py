import marshmallow_recipe as mr


def test_metadata_1() -> None:
    metadata1 = mr.Metadata(dict(a=1, b=2))
    metadata2 = mr.Metadata(dict(b=2, a=1))

    assert hash(metadata1) == hash(metadata2)
    assert metadata1 == metadata2


def test_metadata_2() -> None:
    metadata1 = mr.Metadata(dict(a=1, b=1))
    metadata2 = mr.Metadata(dict(b=2, a=2))

    assert hash(metadata1) == hash(metadata2)
    assert metadata1 != metadata2


def test_metadata_3() -> None:
    metadata1 = mr.Metadata(dict(a=1, b=1))
    metadata2 = mr.Metadata(dict(b=2, c=2))

    assert hash(metadata1) != hash(metadata2)
    assert metadata1 != metadata2
