from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import NewType

VarName = NewType('VarName', str)

@dataclass(frozen=True)
class ArrayElt:
    name: VarName
    subscr: float

class LookupVar:
    @abstractmethod
    def lookup_scalar(self, var: VarName) -> float:
        raise NotImplementedError

    @abstractmethod
    def lookup_array(self, var: ArrayElt) -> float:
        raise NotImplementedError

class Expr:
    def evaluate(self, lookup: LookupVar) -> float:
        raise NotImplementedError

@dataclass(frozen=True)
class ScalarVar(Expr):
    name: VarName
    def evaluate(self, lv: LookupVar) -> float:
        return lv.lookup_scalar(self.name)

@dataclass(frozen=True)
class ArrayVar(Expr):
    name: VarName
    subscr: Expr
    def evaluate(self, lv: LookupVar) -> float:
        return lv.lookup_array(ArrayElt(
            name = self.name,
            subscr = self.subscr.evaluate(lv)
        ))

Var = ScalarVar | ArrayVar

@dataclass(frozen=True)
class Num(Expr):
    val: float
    def evaluate(self, _: LookupVar) -> float:
        return self.val

@dataclass(frozen=True)
class Negate(Expr):
    arg: Expr
    def evaluate(self, lv: LookupVar) -> float:
        return -self.arg.evaluate(lv)
