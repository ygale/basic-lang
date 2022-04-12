from dataclasses import dataclass
from typing import ClassVar, NewType

from expr import Expr, LookupVar

Symbol = NewType('Symbol', str)

@dataclass(frozen=True)
class Op(Expr):
    symbol: ClassVar[Symbol]
    arg1: Expr
    arg2: Expr

class Plus(Op):
    symbol = Symbol('+')
    def evaluate(self, lv: LookupVar) -> float:
        return (self.arg1.evaluate(lv) +
                self.arg2.evaluate(lv))

class Minus(Op):
    symbol = Symbol('-')
    def evaluate(self, lv: LookupVar) -> float:
        return (self.arg1.evaluate(lv) -
                self.arg2.evaluate(lv))

class Times(Op):
    symbol = Symbol('*')
    def evaluate(self, lv: LookupVar) -> float:
        return (self.arg1.evaluate(lv) *
                self.arg2.evaluate(lv))

class Div(Op):
    symbol = Symbol('/')
    def evaluate(self, lv: LookupVar) -> float:
        return (self.arg1.evaluate(lv) /
                self.arg2.evaluate(lv))

TRUE:  float = 1.0
FALSE: float = 0.0

class Eq(Op):
    symbol = Symbol('=')
    def evaluate(self, lv: LookupVar) -> float:
        return (TRUE if
                self.arg1.evaluate(lv) == 
                self.arg2.evaluate(lv)
                else FALSE)

class Ne(Op):
    symbol = Symbol('<>')
    def evaluate(self, lv: LookupVar) -> float:
        return (TRUE if
                self.arg1.evaluate(lv) != 
                self.arg2.evaluate(lv)
                else FALSE)

class Lt(Op):
    symbol = Symbol('<')
    def evaluate(self, lv: LookupVar) -> float:
        return (TRUE if
                self.arg1.evaluate(lv) <
                self.arg2.evaluate(lv)
                else FALSE)

class Le(Op):
    symbol = Symbol('<=')
    def evaluate(self, lv: LookupVar) -> float:
        return (TRUE if
                self.arg1.evaluate(lv) <=
                self.arg2.evaluate(lv)
                else FALSE)

class Gt(Op):
    symbol = Symbol('>')
    def evaluate(self, lv: LookupVar) -> float:
        return (TRUE if
                self.arg1.evaluate(lv) >
                self.arg2.evaluate(lv)
                else FALSE)

class Ge(Op):
    symbol = Symbol('>=')
    def evaluate(self, lv: LookupVar) -> float:
        return (TRUE if
                self.arg1.evaluate(lv) >=
                self.arg2.evaluate(lv)
                else FALSE)
