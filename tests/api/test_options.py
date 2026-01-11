import dataclasses
import decimal

import marshmallow_recipe as mr

from .conftest import Serializer


class TestOptionsNamingCaseDump:
    def test_naming_case_in_options(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(naming_case=mr.CAMEL_CASE)
        class TestFieldContainer:
            test_field: str

        obj = TestFieldContainer(test_field="some_value")
        result = impl.dump(TestFieldContainer, obj)
        assert result == b'{"testField":"some_value"}'

    def test_naming_case_not_affecting_nested(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Container:
            value: str

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(naming_case=mr.CAPITAL_CAMEL_CASE)
        class ContainerContainer:
            value: Container

        obj = ContainerContainer(value=Container(value="some_value"))
        result = impl.dump(ContainerContainer, obj)
        assert result == b'{"Value":{"value":"some_value"}}'


class TestOptionsDecimalPlacesDump:
    def test_decimal_places_in_options(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=4)
        class Container:
            value: decimal.Decimal

        obj = Container(value=decimal.Decimal("123.456789"))
        result = impl.dump(Container, obj)
        assert result == b'{"value":"123.4568"}'

    def test_decimal_places_metadata_overrides_options(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=4)
        class Container:
            value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=1))

        obj = Container(value=decimal.Decimal("123.456789"))
        result = impl.dump(Container, obj)
        assert result == b'{"value":"123.5"}'

    def test_decimal_places_multiple_fields(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=3)
        class Container:
            decimal1: decimal.Decimal
            decimal2: decimal.Decimal
            integer: int

        obj = Container(decimal1=decimal.Decimal("123.456789"), decimal2=decimal.Decimal("987.654321"), integer=42)
        result = impl.dump(Container, obj)
        assert result == b'{"decimal1":"123.457","decimal2":"987.654","integer":42}'

    def test_decimal_places_mixed_options_and_metadata(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=3)
        class Container:
            global_decimal: decimal.Decimal
            field_decimal: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=1))

        obj = Container(global_decimal=decimal.Decimal("123.456789"), field_decimal=decimal.Decimal("123.456789"))
        result = impl.dump(Container, obj)
        assert result == b'{"global_decimal":"123.457","field_decimal":"123.5"}'

    def test_decimal_places_different_classes(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=3)
        class Container3:
            value: decimal.Decimal

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=4)
        class Container4:
            value: decimal.Decimal

        test_value = decimal.Decimal("123.456789")

        result3 = impl.dump(Container3, Container3(value=test_value))
        result4 = impl.dump(Container4, Container4(value=test_value))

        assert result3 == b'{"value":"123.457"}'
        assert result4 == b'{"value":"123.4568"}'

    def test_decimal_places_nested_dataclass(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Inner:
            value: decimal.Decimal

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=3)
        class Outer:
            inner: Inner
            outer_value: decimal.Decimal

        obj = Outer(inner=Inner(value=decimal.Decimal("123.456789")), outer_value=decimal.Decimal("987.654321"))
        result = impl.dump(Outer, obj)
        assert result == b'{"inner":{"value":"123.46"},"outer_value":"987.654"}'

    def test_decimal_places_global_parameter(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Inner:
            value: decimal.Decimal

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Outer:
            inner: Inner
            outer_value: decimal.Decimal

        obj = Outer(inner=Inner(value=decimal.Decimal("123.456789")), outer_value=decimal.Decimal("987.654321"))
        result = impl.dump(Outer, obj, decimal_places=3)
        assert result == b'{"inner":{"value":"123.457"},"outer_value":"987.654"}'

    def test_decimal_places_nested_list(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=3)
        class Item:
            price: decimal.Decimal

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Container:
            items: list[Item]

        obj = Container(items=[Item(price=decimal.Decimal("10.999")), Item(price=decimal.Decimal("20.555"))])
        result = impl.dump(Container, obj)
        assert result == b'{"items":[{"price":"10.999"},{"price":"20.555"}]}'

    def test_decimal_places_deeply_nested(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Level3:
            value: decimal.Decimal

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Level2:
            level3: Level3

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=1)
        class Level1:
            level2: Level2

        obj = Level1(level2=Level2(level3=Level3(value=decimal.Decimal("123.456"))))
        result = impl.dump(Level1, obj)
        assert result == b'{"level2":{"level3":{"value":"123.46"}}}'


class TestOptionsDecimalPlacesLoad:
    def test_decimal_places_in_options(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=4)
        class Container:
            value: decimal.Decimal

        data = b'{"value":"123.456789"}'
        result = impl.load(Container, data)
        assert result == Container(value=decimal.Decimal("123.4568"))

    def test_decimal_places_metadata_overrides_options(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(decimal_places=4)
        class Container:
            value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=1))

        data = b'{"value":"123.456789"}'
        result = impl.load(Container, data)
        assert result == Container(value=decimal.Decimal("123.5"))

    def test_decimal_places_global_parameter(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Inner:
            value: decimal.Decimal

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Outer:
            inner: Inner

        data = b'{"inner":{"value":"123.456789"}}'
        result = impl.load(Outer, data, decimal_places=3)
        assert result == Outer(inner=Inner(value=decimal.Decimal("123.457")))


class TestOptionsNoneValueHandlingDump:
    def test_none_value_handling_include(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DataClass:
            str_field: str | None = None
            int_field: int | None = None

        obj = DataClass(str_field="hello", int_field=None)
        result = impl.dump(DataClass, obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"str_field":"hello","int_field":null}'

    def test_none_value_handling_ignore(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DataClass:
            str_field: str | None = None
            int_field: int | None = None

        obj = DataClass(str_field="hello", int_field=None)
        result = impl.dump(DataClass, obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b'{"str_field":"hello"}'

    def test_none_value_handling_override(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        @mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
        class DataClass:
            str_field: str | None = None
            int_field: int | None = None

        obj = DataClass(str_field="hello", int_field=None)

        result_override = impl.dump(DataClass, obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result_override == b'{"str_field":"hello"}'

        result_default = impl.dump(DataClass, obj)
        assert result_default == b'{"str_field":"hello","int_field":null}'
