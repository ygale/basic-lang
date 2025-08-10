from dataclasses import dataclass, field
from exceptions import EvalError
from expr import ArrayElt, LookupVar, VarName
from typing import NewType

LineNum = NewType('LineNum', int)

class StopRun:
  pass

@dataclass
class ForLoop:
  var: VarName
  first_line: int
  to: float
  step: float = 1.0

@dataclass
class RunState[Stmt](LookupVar):
  prog: list[Stmt] = field(default_factory=list)
  line_map: dict[LineNum, int] = field(
    default_factory=dict)
  addr: int = 0
  goto: int | StopRun | None = None
  scalars: dict[VarName, float] = field(
    default_factory=dict)
  arrays: dict[VarName, list[float | None]] = field(
    default_factory=dict)
  for_loops: dict[VarName, ForLoop] = field(
    default_factory=dict)
  data: list[float] = field(default_factory=list)
  data_cursor: int = 0

  def lookup_scalar(self, var: VarName) -> float:
    try:
      return self.scalars[var]
    except KeyError:
      raise EvalError(f'variable {var} is undefined')

  def lookup_array(self, var: ArrayElt) -> float:
    try:
      val: float | None = (
        self.arrays[var.name][int(var.subscr) - 1])
    except KeyError:
      raise EvalError(f'array {var.name} has no DIM')
    except IndexError:
      raise EvalError(' '.join([
        f'subscript {var.subscr} is out of range',
        f'for array {var.name}']))
    if val is None:
      raise EvalError(' '.join([
        f'array element {var.name}[{var.subscr}]',
        'is undefined']))
    else:
      return val
