from dataclasses import dataclass
from pysh import types_, vals

from unittest import TestCase


@dataclass(frozen=True)
class Int(vals.Val):
    value: int

    @property
    def type(self) -> types_.Type:
        return types_.BuiltinType('int')

    @property
    def members(self) -> vals.Scope:
        return vals.Scope({})


@dataclass(frozen=True)
class Str(vals.Val):
    value: str

    @property
    def type(self) -> types_.Type:
        return types_.BuiltinType('str')

    @property
    def members(self) -> vals.Scope:
        return vals.Scope({})


class VarTest(TestCase):
    pass
