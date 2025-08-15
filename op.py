from dataclasses import dataclass
from exceptions import EvalError
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
class UnaryOp(Op):
  arg: Expr
  precedence = 4
  def pprint(self) -> str:
    return (self.symbol +
            self.arg.pprint_prec(self.precedence))

@dataclass
class Negate(UnaryOp):
  symbol = Symbol('-')
  def evaluate(self, lv: LookupVar) -> float:
    return -self.arg.evaluate(lv)

@dataclass
class Positive(UnaryOp):
  symbol = Symbol('+')
  def evaluate(self, lv: LookupVar) -> float:
    return self.arg.evaluate(lv)

all_unaryops: list[type[UnaryOp]] = [Negate, Positive]

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
    try:
      return (self.arg1.evaluate(lv) /
              self.arg2.evaluate(lv))
    except ZeroDivisionError:
      raise EvalError('division by zero')

class Power(BinOp):
  symbol = Symbol('^')
  precedence = 4
  def evaluate(self, lv: LookupVar) -> float:
    try:
      val: float | complex = (
        self.arg1.evaluate(lv) **
        self.arg2.evaluate(lv))
    except ZeroDivisionError:
      raise EvalError('negative power of zero')
    except OverflowError:
      raise EvalError('number is too large')
    if isinstance(val, float):
      return val
    else:
      raise EvalError('fractional power of a negative')

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

all_binops: list[type[BinOp]] = [ # order matters
  Plus, Minus, Times, Div, Power, Eq, Ne, Le, Ge, Lt, Gt]
