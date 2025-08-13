from abc import abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import NewType

VarName = NewType('VarName', str)

@dataclass
class ArrayElt:
    '''A reference to an element of an array.'''
    name: VarName
    subscr: float

class LookupVar:
    '''A symbol table for looking up the values of
    variables while evaluating an expression.
    Raises EvalError if the variable is undefined.'''
    @abstractmethod
    def lookup_scalar(self, var: VarName) -> float:
        raise NotImplementedError

    @abstractmethod
    def lookup_array(self, var: ArrayElt) -> float:
        raise NotImplementedError

class Expr:
    '''An expression.'''
    @abstractmethod
    def pprint(self) -> str:
        '''Pretty-print.'''
        raise NotImplementedError

    def pprint_prec(self, prec: int) -> str:
        '''Pretty-print an expression nested as a
        parameter of an operator with the given
        precedence.'''
        # By default ignore the precedence, unless
        # this is itself an operator.
        return self.pprint()

    @abstractmethod
    def evaluate(self, lookup: LookupVar) -> float:
        '''Evaluate the value of the expression.'''
        raise NotImplementedError

@dataclass
class Var(Expr):
    '''A reference to a variable in an expression.'''
    name: VarName

@dataclass
class ScalarVar(Var):
    '''A reference to a scalar variable in an
    expression.'''
    def pprint(self) -> str:
        return self.name
    def evaluate(self, lv: LookupVar) -> float:
        return lv.lookup_scalar(self.name)

@dataclass
class ArrayVar(Var):
    '''A reference to an element of an array in an
    expression.'''
    subscr: Expr
    def pprint(self) -> str:
        return f'{self.name}[{self.subscr.pprint()}]'
    def evaluate(self, lv: LookupVar) -> float:
        return lv.lookup_array(ArrayElt(
            name = self.name,
            subscr = self.subscr.evaluate(lv)
        ))

@dataclass
class Num(Expr):
    '''A numeric literal.'''
    val: float
    def pprint(self) -> str:
      return pprint_float(self.val)
    def evaluate(self, _: LookupVar) -> float:
        return self.val

def pprint_float(x: float) -> str:
  '''Omit the zero decimal part when pretty printing
  integers.'''
  if x.is_integer():
    return str(int(x))
  else:
    return str(x)

@dataclass
class Parens(Expr):
    '''A parenthesized subexpression.'''
    expr: Expr
    def pprint(self) -> str:
        return f'({self.expr.pprint()})'
    def evaluate(self, lv: LookupVar) -> float:
        return self.expr.evaluate(lv)
