from dataclasses import dataclass
import math
from typing import ClassVar, NewType

from expr import Expr, LookupVar

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
    return 0.0 if val == 0.0 else (
      math.copysign(1.0, val))

class Sqr(Func):
  name = FuncName('SQR')
  def evaluate(self, lv: LookupVar) -> float:
    return math.sqrt(self.arg.evaluate(lv))

class Log(Func):
  name = FuncName('LOG')
  def evaluate(self, lv: LookupVar) -> float:
    return math.log(self.arg.evaluate(lv))

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

all_funcs: list[type[Func]] = [
  Int, Abs, Sgn, Sqr, Log, Exp, Sin, Cos, Tan, Atn]
