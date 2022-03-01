import dataclasses
from typing import Protocol


class NamingCase(Protocol):
    def __call__(self, name: str) -> str:
        ...


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CapitalCamelCase:
    capitalize_words: frozenset[str]

    def __call__(self, name: str) -> str:
        return "".join(self._process_word(word) for word in name.split("_") if word)

    def _process_word(self, word: str) -> str:
        if not word[0].isalpha():
            return word
        if word in self.capitalize_words:
            return word.upper()
        return word.title()


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CamelCase:
    capitalize_words: frozenset[str]

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
class _Default:
    def __call__(self, name: str) -> str:
        return name


CAPITAL_CAMEL_CASE = CapitalCamelCase(capitalize_words=frozenset())
CAMEL_CASE = CamelCase(capitalize_words=frozenset())
DEFAULT_CASE = _Default()
