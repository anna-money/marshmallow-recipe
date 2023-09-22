## v0.0.27(2023-09-22)

* [Basic support of Annotated fields](https://github.com/anna-money/marshmallow-recipe/pull/123)
* [Stop using typing_inspect](https://github.com/anna-money/marshmallow-recipe/pull/122)


## v0.0.26(2023-09-18)

* [Support python 3.12](https://github.com/anna-money/marshmallow-recipe/pull/121)


## v0.0.25(2023-09-11)

* Support set, set[T], frozenset, frozenset[T], tuple, tuple[T, ...], collections.abc.Set[T], collections.abc.Sequence[T], collections.abc.Mapping[K, V]


## v0.0.24(2023-09-08)

* [Set __module__ for auto-generated schemas](https://github.com/anna-money/marshmallow-recipe/pull/112)
* [Calling bake_schema should reuse already generated schemas](https://github.com/anna-money/marshmallow-recipe/pull/113)
* [NamingCase should not be propagated through serialisation hierarchy](https://github.com/anna-money/marshmallow-recipe/pull/113)
* [Removal of DEFAULT_CASE](https://github.com/anna-money/marshmallow-recipe/pull/113)


## v0.0.23(2023-09-05)

* [Validate dumped data against its schema for marshmallow2](https://github.com/anna-money/marshmallow-recipe/pull/110)


## v0.0.22(2023-06-27)


## v0.0.22a2(2023-06-27)

* [Support typed dict key](https://github.com/anna-money/marshmallow-recipe/pull/104)


## v0.0.22a1(2023-06-24)

* [Support typed dict value](https://github.com/anna-money/marshmallow-recipe/pull/101)


## v0.0.21(2023-06-24)


## v0.0.21a1(2023-06-08)

* [Cache intermediate schema types](https://github.com/anna-money/marshmallow-recipe/pull/98)


## v0.0.20(2023-04-25)

* [Allow to validate list item](https://github.com/anna-money/marshmallow-recipe/pull/95)


## v0.0.19(2023-04-24)

* [Allow validations for nested/list/dict/enum](https://github.com/anna-money/marshmallow-recipe/pull/94)


## v0.0.18(2023-01-05)

* [Allow to specify default_factory](https://github.com/anna-money/marshmallow-recipe/pull/82)


## v0.0.17(2022-12-20)

* [Non-optional fields with default value might not present in data](https://github.com/anna-money/marshmallow-recipe/pull/76)


## v0.0.16(2022-12-02)

* [Do not modify input data for marshmallow<3](https://github.com/anna-money/marshmallow-recipe/pull/72)


## v0.0.15(2022-12-01)

* [Metadata name should not use others field name](https://github.com/anna-money/marshmallow-recipe/pull/71)
* [Ignore unknown fields for marshmallow2](https://github.com/anna-money/marshmallow-recipe/pull/70)


## v0.0.14(2022-11-14)

* [Do not crash if an unknown arg is passed to enum meta](https://github.com/anna-money/marshmallow-recipe/pull/67)


## v0.0.13(2022-10-14)

* [Add pre_load hooks](https://github.com/anna-money/marshmallow-recipe/pull/62)


## v0.0.12(2022-08-23)

* [Add datetime_metadata to allow to specify a custom format](https://github.com/anna-money/marshmallow-recipe/pull/55)


## v0.0.11(2022-06-23)

* [Add options, MISSING, none_value_handling](https://github.com/anna-money/marshmallow-recipe/pull/47)


## v0.0.10(2022-06-15)

* [Fix input of load_many](https://github.com/anna-money/marshmallow-recipe/pull/46)


## v0.0.9(2022-04-26)

* [Support Any](https://github.com/Pliner/marshmallow-recipe/pull/42)


## v0.0.8(2022-03-26)

* [Allow default value for required fields](https://github.com/Pliner/marshmallow-recipe/pull/39)


## v0.0.7(2022-03-20)

* [Support validation](https://github.com/Pliner/marshmallow-recipe/pull/37)


## v0.0.6(2022-03-20)

* [Support enum](https://github.com/Pliner/marshmallow-recipe/pull/36)
* [Add empty schema](https://github.com/Pliner/marshmallow-recipe/pull/31)


## v0.0.5(2022-03-01)

* [Validate before dump for marshmallow3](https://github.com/Pliner/marshmallow-recipe/pull/25)
* [Move many to schema](https://github.com/Pliner/marshmallow-recipe/pull/27)
* [Fix default naming case](https://github.com/Pliner/marshmallow-recipe/pull/29)
* [Fix unhashable type: 'set' error](https://github.com/Pliner/marshmallow-recipe/pull/30)


## v0.0.4(2022-02-21)

* [Support decimal field](https://github.com/Pliner/marshmallow-recipe/pull/10)
* [Support metadata](https://github.com/Pliner/marshmallow-recipe/pull/11)
* [Support int field](https://github.com/Pliner/marshmallow-recipe/pull/13)
* [Support float field](https://github.com/Pliner/marshmallow-recipe/pull/14)
* [Support uuid field](https://github.com/Pliner/marshmallow-recipe/pull/15)
* [Support list and dict](https://github.com/Pliner/marshmallow-recipe/pull/19)
* [Support marshmallow3](https://github.com/Pliner/marshmallow-recipe/pull/20)
* [Support datetime and date](https://github.com/Pliner/marshmallow-recipe/pull/21)
* [Unify datetime.tzinfo behaviour](https://github.com/Pliner/marshmallow-recipe/pull/22)


## v0.0.3 (2022-02-14)

* [Unify behaviour of nested_field in line with str_field/bool_field](https://github.com/Pliner/marshmallow-recipe/pull/9)
* [Rearrange api](https://github.com/Pliner/marshmallow-recipe/pull/8)


## v0.0.2 (2022-02-13)

* [Customize capital camel case and add camel case](https://github.com/Pliner/marshmallow-recipe/pull/6)


## v0.0.1 (2022-02-13)

* A first version
