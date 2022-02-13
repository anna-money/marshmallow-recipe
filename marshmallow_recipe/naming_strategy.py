from typing import Callable


def capital_camel_case_factory(*, capitalize_words: set[str]) -> Callable[[str], str]:
    def _process_word(word: str) -> str:
        if not word[0].isalpha():
            return word
        if word in capitalize_words:
            return word.upper()
        return word.title()

    def _capital_camel_case(name: str) -> str:
        return "".join(_process_word(word) for word in name.split("_") if word)

    return _capital_camel_case


def camel_case_factory(*, capitalize_words: set[str]) -> Callable[[str], str]:
    def _process_word(word: str) -> str:
        if not word[0].isalpha():
            return word
        if word in capitalize_words:
            return word.upper()
        return word.title()

    def _camel_case(name: str) -> str:
        words = [word for word in name.split("_") if word]
        return "".join([words[0]] + [_process_word(word) for word in words[1:]])

    return _camel_case


capital_camel_case = capital_camel_case_factory(capitalize_words=set())
camel_case = camel_case_factory(capitalize_words=set())
