from dataclasses import dataclass
from typing import ClassVar, NewType

from expr import Expr, LookupVar

Symbol = NewType('Symbol', str)

@dataclass
class Op(Expr):
  symbol: ClassVar[Symbol]
  precedence: ClassVar[int]
  def pprint_prec(self, prec: int) -> str:
    if prec > self.precedence:
      return f'({self.pprint()})'
    else:
      return self.pprint()

@dataclass
class Negate(Op):
  arg: Expr
  symbol = Symbol('-')
  precedence = 4
  def pprint(self) -> str:
    return (self.symbol +
            self.arg.pprint_prec(self.precedence))
  def evaluate(self, lv: LookupVar) -> float:
    return -self.arg.evaluate(lv)

@dataclass
class BinOp(Op):
  arg1: Expr
  arg2: Expr
  def pprint(self) -> str:
    return ' '.join([
      self.arg1.pprint_prec(self.precedence),
      self.symbol,
      self.arg2.pprint_prec(self.precedence)])

class Plus(BinOp):
  symbol = Symbol('+')
  precedence = 2
  def evaluate(self, lv: LookupVar) -> float:
      return (self.arg1.evaluate(lv) +
              self.arg2.evaluate(lv))

class Minus(BinOp):
  symbol = Symbol('-')
  precedence = 2
  def evaluate(self, lv: LookupVar) -> float:
      return (self.arg1.evaluate(lv) -
              self.arg2.evaluate(lv))

class Times(BinOp):
  symbol = Symbol('*')
  precedence = 3
  def evaluate(self, lv: LookupVar) -> float:
      return (self.arg1.evaluate(lv) *
              self.arg2.evaluate(lv))

class Div(BinOp):
  symbol = Symbol('/')
  precedence = 3
  def evaluate(self, lv: LookupVar) -> float:
      return (self.arg1.evaluate(lv) /
              self.arg2.evaluate(lv))

TRUE:  float = 1.0
FALSE: float = 0.0

class Eq(BinOp):
  symbol = Symbol('=')
  precedence = 1
  def evaluate(self, lv: LookupVar) -> float:
      return (TRUE if
              self.arg1.evaluate(lv) == 
              self.arg2.evaluate(lv)
              else FALSE)

class Ne(BinOp):
  symbol = Symbol('<>')
  precedence = 1
  def evaluate(self, lv: LookupVar) -> float:
      return (TRUE if
              self.arg1.evaluate(lv) != 
              self.arg2.evaluate(lv)
              else FALSE)

class Lt(BinOp):
  symbol = Symbol('<')
  precedence = 1
  def evaluate(self, lv: LookupVar) -> float:
      return (TRUE if
              self.arg1.evaluate(lv) <
              self.arg2.evaluate(lv)
              else FALSE)

class Le(BinOp):
  symbol = Symbol('<=')
  precedence = 1
  def evaluate(self, lv: LookupVar) -> float:
      return (TRUE if
              self.arg1.evaluate(lv) <=
              self.arg2.evaluate(lv)
              else FALSE)

class Gt(BinOp):
  symbol = Symbol('>')
  precedence = 1
  def evaluate(self, lv: LookupVar) -> float:
      return (TRUE if
              self.arg1.evaluate(lv) >
              self.arg2.evaluate(lv)
              else FALSE)

class Ge(BinOp):
  symbol = Symbol('>=')
  precedence = 1
  def evaluate(self, lv: LookupVar) -> float:
      return (TRUE if
              self.arg1.evaluate(lv) >=
              self.arg2.evaluate(lv)
              else FALSE)

all_binops: list[type[BinOp]] = [
  Plus, Minus, Times, Div, Eq, Ne, Lt, Le, Gt, Ge]
