from basic.exceptions import EvalError
from basic.expr import Expr, LookupVar
from dataclasses import dataclass
import math
import random
from typing import ClassVar, NewType

FuncName = NewType('FuncName', str)

@dataclass
class Func(Expr):
  name: ClassVar[FuncName]
  arg: Expr
  def pprint(self) -> str:
    return f'{self.name}({self.arg.pprint()})'

class Int(Func):
  name = FuncName('INT')
  def evaluate(self, lv: LookupVar) -> float:
    return math.trunc(self.arg.evaluate(lv))

class Abs(Func):
  name = FuncName('ABS')
  def evaluate(self, lv: LookupVar) -> float:
    return math.fabs(self.arg.evaluate(lv))

class Sgn(Func):
  name = FuncName('SGN')
  def evaluate(self, lv: LookupVar) -> float:
    val: float = self.arg.evaluate(lv)
    # careful about -0.0
    return 0.0 if val == 0.0 else math.copysign(1.0, val)

class Sqr(Func):
  name = FuncName('SQR')
  def evaluate(self, lv: LookupVar) -> float:
    arg: float = self.arg.evaluate(lv)
    try:
      return math.sqrt(arg)
    except ValueError:
      if arg < 0.0:
        raise EvalError('SQR of a negative number')
      else:
        # should never happen
        raise EvalError('SQR of an invalid number')

class Log(Func):
  name = FuncName('LOG')
  def evaluate(self, lv: LookupVar) -> float:
    arg: float = self.arg.evaluate(lv)
    try:
      return math.log(arg)
    except ValueError:
      if arg == 0.0:
        raise EvalError('LOG of zero')
      elif arg < 0.0:
        raise EvalError('LOG of a negative number')
      else:
        # should never happen
        raise EvalError('LOG of an invalid number')

class Exp(Func):
  name = FuncName('EXP')
  def evaluate(self, lv: LookupVar) -> float:
    return math.exp(self.arg.evaluate(lv))

class Sin(Func):
  name = FuncName('SIN')
  def evaluate(self, lv: LookupVar) -> float:
    return math.sin(self.arg.evaluate(lv))

class Cos(Func):
  name = FuncName('COS')
  def evaluate(self, lv: LookupVar) -> float:
    return math.cos(self.arg.evaluate(lv))

class Tan(Func):
  name = FuncName('TAN')
  def evaluate(self, lv: LookupVar) -> float:
    return math.tan(self.arg.evaluate(lv))

class Atn(Func):
  name = FuncName('ATN')
  def evaluate(self, lv: LookupVar) -> float:
    return math.atan(self.arg.evaluate(lv))

class Rnd(Func):
  name = FuncName('RND')
  def evaluate(self, lv: LookupVar) -> float:
    return random.random()

all_funcs: list[type[Func]] = [
  Int, Abs, Sgn, Sqr, Log, Exp, Sin, Cos, Tan, Atn, Rnd]
