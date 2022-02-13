def capital_camel_case(name: str) -> str:
    return "".join(part.title() if part[0].isalpha() else part for part in name.split("_") if part)
