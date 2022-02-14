import dataclasses
from typing import Protocol


class NamingCase(Protocol):
    __slots__ = ()

    def __call__(self, name: str) -> str:
        ...


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CapitalCamelCase(NamingCase):
    capitalize_words: set[str]

    def __call__(self, name: str) -> str:
        return "".join(self._process_word(word) for word in name.split("_") if word)

    def _process_word(self, word: str) -> str:
        if not word[0].isalpha():
            return word
        if word in self.capitalize_words:
            return word.upper()
        return word.title()


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CamelCase(NamingCase):
    capitalize_words: set[str]

    def __call__(self, name: str) -> str:
        words = [word for word in name.split("_") if word]
        return "".join([words[0]] + [self._process_word(word) for word in words[1:]])

    def _process_word(self, word: str) -> str:
        if not word[0].isalpha():
            return word
        if word in self.capitalize_words:
            return word.upper()
        return word.title()


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Default(NamingCase):
    pass


CAPITAL_CAMEL_CASE = CapitalCamelCase(capitalize_words=set())
CAMEL_CASE = CamelCase(capitalize_words=set())
DEFAULT_CASE = _Default()
