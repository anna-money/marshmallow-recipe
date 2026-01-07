## v0.0.69 (unreleased)

* [Add JsonRawField with JSON validation for Any type fields](https://github.com/anna-money/marshmallow-recipe/pull/212)
* [Fix UUID invalid_error not being applied](https://github.com/anna-money/marshmallow-recipe/pull/213)
* [Fix int values being converted to float when dumping float fields](https://github.com/anna-money/marshmallow-recipe/pull/214)
* Switch to VCS-based versioning with hatch-vcs
* [Fix collection field error messages](https://github.com/anna-money/marshmallow-recipe/pull/216)
* [Strict enum type checking and reject bool for int/float fields on dump](https://github.com/anna-money/marshmallow-recipe/pull/219)
* [Add `frozenset_meta`/`frozenset_metadata` for consistency with other collection types](https://github.com/anna-money/marshmallow-recipe/pull/220)


## v0.0.68 (2025-12-16)

* Add `description` parameter to all metadata functions (`mr.meta`, `mr.str_meta`, `mr.decimal_meta`, `mr.datetime_meta`, `mr.time_meta`, `mr.list_meta`, `mr.set_meta`, `mr.tuple_meta`)
* Field descriptions are passed to marshmallow Fields via the metadata dictionary (marshmallow v3) or as direct kwargs (marshmallow v2)
* Updated examples to demonstrate description usage


## v0.0.67 (2025-12-02)

* Return Dataclass protocol back because it has already been used


## v0.0.66 (2025-12-01)

* [Use PEP 695, Drop Python 3.11 support](https://github.com/anna-money/marshmallow-recipe/pull/205)
* Revert T binding in dump/load/dump_many/load_many/schema to dataclass only introduced in 0.0.65


## v0.0.65 (2025-11-08)

* [Ensure T is bound by dataclass for dump/load/dump_many/load_many/schema](https://github.com/anna-money/marshmallow-recipe/pull/203)
* [Ensure T is bound by dataclass for schema(https://github.com/anna-money/marshmallow-recipe/commit/ff75a88d4b8e3d2ea2eede020dbe3b33f70f4468)
* [Add support of python 3.14](https://github.com/anna-money/marshmallow-recipe/pull/202)


## v0.0.64 (2025-11-03)

* Add custom error message support via `required_error`, `none_error`, and `invalid_error` parameters to all field and metadata functions


## v0.0.63(2025-10-21)

* [Restrict email validation for quoted local-parts](https://github.com/anna-money/marshmallow-recipe/pull/199)


## v0.0.62(2025-10-15)

* Add email validation support with mr.email_validate()


## v0.0.61(2025-10-06)

* Add rounding parameter support for decimal fields via decimal_meta()


## v0.0.61a1(2025-10-06)

* Add rounding parameter support for decimal fields via decimal_meta()


## v0.0.60(2025-10-06)

* Add comprehensive examples covering all library functionality
* Add Context7 configuration for AI-assisted development
* Improve README.md with examples documentation
* Update CLAUDE.md with documentation maintenance requirements


## v0.0.59(2025-09-30)

* [Fix decimal_places parameter not propagating to nested dataclasses](https://github.com/anna-money/marshmallow-recipe/pull/192)
* [Fix decimal_places propagation behavior to be consistent with naming_case and none_value_handling](https://github.com/anna-money/marshmallow-recipe/pull/193)


## v0.0.58(2025-09-30)

* [Add global none_value_handling parameter to load/dump functions](https://github.com/anna-money/marshmallow-recipe/pull/191)


## v0.0.57(2025-08-22)

* [Cyclic references support](https://github.com/anna-money/marshmallow-recipe/pull/189)


## v0.0.56(2025-08-14)

* [Allow to override decimal places per class and globally](https://github.com/anna-money/marshmallow-recipe/pull/188)


## v0.0.55(2025-07-23)

* [If datetime is passed as a date, use only date part of it](https://github.com/anna-money/marshmallow-recipe/pull/187)


## v0.0.54(2025-07-18)

* [Float field should consume int](https://github.com/anna-money/marshmallow-recipe/pull/186)


## v0.0.53(2025-06-26)

* [Support unions](https://github.com/anna-money/marshmallow-recipe/pull/182)


## v0.0.52(2025-05-21)

* [Support upper snake case](https://github.com/anna-money/marshmallow-recipe/pull/183)


## v0.0.51(2025-05-15)

* [Support typing.NewType](https://github.com/anna-money/marshmallow-recipe/pull/181)


## v0.0.50(2025-05-10)

* [Make Metadata hashable](https://github.com/anna-money/marshmallow-recipe/pull/180)


## v0.0.49(2025-05-03)

* [Fix support of unsubscripted Mapping](https://github.com/anna-money/marshmallow-recipe/pull/178)


## v0.0.48(2025-04-23)

* [Allow to set no places for decimal](https://github.com/anna-money/marshmallow-recipe/pull/175)


## v0.0.47(2025-04-07)

* [Support generics](https://github.com/anna-money/marshmallow-recipe/pull/163)


## v0.0.46(2025-04-07)

* [Make cls/data positional arguments only](https://github.com/anna-money/marshmallow-recipe/commit/ef4e41a105c08876a9cf9d3f13c1e5f9c2fbb37b)


## v0.0.45(2025-03-19)

* [Get marshmallow version using importlib.metadata](https://github.com/anna-money/marshmallow-recipe/pull/170)


## v0.0.44(2025-02-04)

* [Fix strip whitespaces with validation](https://github.com/anna-money/marshmallow-recipe/pull/168)


## v0.0.43(2024-11-11)

* [Fix python_requires to be >=3.11](https://github.com/anna-money/marshmallow-recipe/commit/ab1eca29324569dbcc712f589078eee9980f9b10)
* [Switch to StrEnum](https://github.com/anna-money/marshmallow-recipe/commit/e732d5a6c96f3316f7d33d903f15680f83b63fbe)


## v0.0.42(2024-11-09)

* [Preserve declaration order](https://github.com/anna-money/marshmallow-recipe/pull/164)


## v0.0.41(2024-11-01)

* [Int enum support](https://github.com/anna-money/marshmallow-recipe/pull/161)
* [Remove unused extendable_default](https://github.com/anna-money/marshmallow-recipe/commit/e45280d5567c12acf6b82f88a34972a482ed3805)


## v0.0.40(2024-10-28)

* [Add support of python 3.13](https://github.com/anna-money/marshmallow-recipe/pull/158)
* [Ditch support of python 3.10](https://github.com/anna-money/marshmallow-recipe/pull/160)


## v0.0.39(2024-07-25)

* [Suppress deprecation warning because of version detection](https://github.com/anna-money/marshmallow-recipe/pull/153)


## v0.0.38(2024-01-05)

* [Min support marshmallow is 2.20.5](https://github.com/anna-money/marshmallow-recipe/pull/145)


## v0.0.38a2(2023-12-15)

* [Almost stop using marshmallow defaults (except Nones)](https://github.com/anna-money/marshmallow-recipe/pull/143)


## v0.0.38a1(2023-12-11)

* [Use native isoformat/fromisoformat](https://github.com/anna-money/marshmallow-recipe/pull/141)


## v0.0.37(2023-12-11)

* [Cache get_pre_loads results](https://github.com/anna-money/marshmallow-recipe/pull/140)


## v0.0.36(2023-12-08)

* [Fix nullable with nested annotation](https://github.com/anna-money/marshmallow-recipe/pull/139)


## v0.0.34(2023-12-07)

* Support datetime.time: [#137](https://github.com/anna-money/marshmallow-recipe/pull/137)


## v0.0.33(2023-09-30)

* Add validation field errors: [#133](https://github.com/anna-money/marshmallow-recipe/pull/133), [9f13f05](https://github.com/anna-money/marshmallow-recipe/commit/9f13f058f9c2e26ab91e482431a38e755a7efcee)


## v0.0.32(2023-09-28)

* [Validate by regexp/Validate with a custom error](https://github.com/anna-money/marshmallow-recipe/pull/132) 


## v0.0.31(2023-09-26)

* [Allow to strip whitespaces on load/dump for str fields](https://github.com/anna-money/marshmallow-recipe/pull/130) 
* [Allow to provide post_load delegate for str fields](https://github.com/anna-money/marshmallow-recipe/pull/131)


## v0.0.30(2023-09-25)

* [Improve validation support: expose ValidationError to raise it from validators, allow to pass a sequence of validators](https://github.com/anna-money/marshmallow-recipe/pull/129) 
* [Add meta shortcuts to metadata methods](https://github.com/anna-money/marshmallow-recipe/pull/128)


## v0.0.29(2023-09-23)

* Allow to use metadata as part of Annotated: [#126](https://github.com/anna-money/marshmallow-recipe/pull/126) and  [#127](https://github.com/anna-money/marshmallow-recipe/pull/127). 


## v0.0.28(2023-09-22)

* [Fix options decorator](https://github.com/anna-money/marshmallow-recipe/pull/125)


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
