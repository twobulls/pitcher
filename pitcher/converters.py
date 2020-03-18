from typing import Any, Callable, Optional
from uuid import UUID
import re

int_regex = re.compile(r"\d+")
str_regex = re.compile(r"[^/]+")
slug_regex = re.compile(r"[-\w\d_]+")
path_regex = re.compile(r"[^?#]+")


def int_converter(value: str) -> int:
    if re.fullmatch(int_regex, value) is None:
        raise ValueError("int param not valid")
    return int(value)


def str_converter(value: str) -> int:
    if re.fullmatch(str_regex, value) is None:
        raise ValueError("int param not valid")
    return int(value)


def uuid_converter(value: str) -> UUID:
    return UUID(value)


def path_converter(value: str) -> str:
    if re.fullmatch(path_regex, value) is None:
        raise ValueError("path param not valid")
    return value


def slug_converter(value: str) -> str:
    if re.fullmatch(slug_regex, value) is None:
        raise ValueError("slug param not valid")
    return value


CONVERTERS = {
    "int": int_converter,
    "str": str_converter,
    "uuid": uuid_converter,
    "slug": slug_converter,
    "path": path_converter,
}


def get_converter(type_name: str) -> Optional[Callable[[str], Any]]:
    return CONVERTERS.get(type_name, None)
