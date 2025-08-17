from dataclasses import dataclass, field
from exceptions import EvalError
from expr import ArrayElt, LookupVar, pprint_float, VarName
from typing import Callable, Concatenate, NewType

LineNum = NewType('LineNum', int)

class StopRun:
  pass

@dataclass
class ForLoop:
  var: VarName
  first_line: int
  to: float
  step: float = 1.0
  parent: VarName | None = None

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
  inner_for: VarName | None = None
  data: list[float] = field(default_factory=list)
  data_cursor: int = 0

  def lookup_scalar(self, var: VarName) -> float:
    try:
      return self.scalars[var]
    except KeyError:
      raise EvalError(f'variable {var} is undefined')

  def lookup_array(self, var: ArrayElt) -> float:
    return self.safe_array_op(
      var,
      self.unsafe_lookup_array)

  def unsafe_lookup_array(self, var: ArrayElt) -> float:
    val: float | None = (
        self.arrays[var.name][int(var.subscr) - 1])
    if val is None:
      raise EvalError(' '.join([
        f'array element {var.name}[{var.subscr}]',
        'is undefined']))
    else:
      return val

  def set_array_elt(
      self,
      var: ArrayElt,
      val: float
      ) -> None:
    return self.safe_array_op(
      var, self.unsafe_set_array_elt, val)

  def unsafe_set_array_elt(
      self,
      var: ArrayElt,
      val: float
      ) -> None:
    self.arrays[var.name][int(var.subscr) - 1] = val

  def safe_array_op[Output, **P](
      self,
      var: ArrayElt,
      op: Callable[
        Concatenate[ArrayElt, P],
        Output],
      *args: P.args,
      **kwargs: P.kwargs
      ) -> Output:
    try:
      return op(var, *args, **kwargs)
    except KeyError:
      raise EvalError(f'array {var.name} has no DIM')
    except IndexError:
      subscr: str = pprint_float(var.subscr)
      raise EvalError(' '.join([
        f'subscript {subscr} is out of range',
        f'for array {var.name}']))
