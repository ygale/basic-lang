from expr import (ArrayVar, Expr, Num, ScalarVar, Var,
  VarName)
from func import all_funcs, Func
from op import all_binops, BinOp, Negate
from parser import (ap, attempt, choice, digit1, fail,
  lit, lit_ci, NoParse, optional, ParserState, regex,
  space)
import re

type PS = ParserState[str]

def parse_expr(s: PS) -> Expr:
  '''Parse an expression.'''
  expr: Expr = non_op(s)
  return ops(s, expr)

def non_op(s: PS) -> Expr:
  '''Parse an expression whose top level is not a binary
  operator.'''
  space(s)
  expr: Expr | None = optional(s, ap(choice, [
    paren_expr,
    num_expr,
    func_expr,
    var_expr,
    neg_expr]))
  if expr is None:
    fail(s,
         expected='expression',
         found=s._input[s.context.cursor:])
  else:
    return expr

def ops(s: PS, expr: Expr) -> Expr:
  '''Parse a sequence of binary operators.'''
  # push operators in strictly increasing order of
  # precedence onto a stack
  stack: list[tuple[Expr, type[BinOp]]] = []
  while True:
    expr1: Expr
    expr2: Expr
    op_cls1: type[BinOp]
    op_cls2: type[BinOp]
    space(s)
    try:
      op_cls2 = op_class(s)
    except NoParse:
      # no more operators, unwind the stack
      while len(stack) > 0:
        expr1, op_cls1 = stack.pop()
        expr = op_cls1(expr1, expr)
      return expr
    try:
      expr2 = non_op(s)
    except NoParse:
      fail(s,
           expected=f'expression after "{op_cls2.symbol}"',
           found=s._input[s.context.cursor:])
    # pop the stack until the top has strictly lower
    # precedence than the one we found, or until the stack
    # is empty. then push the one we found onto the stack.
    while (len(stack) > 0 and
           op_cls2.precedence <= stack[-1][1].precedence):
      expr1, op_cls1 = stack.pop()
      expr = op_cls1(expr1, expr)
    stack.append((expr, op_cls2))
    expr = expr2

def op_class(s: PS) -> type[BinOp]:
  '''Parse a binary operator symbol and return its 
  class.'''
  return choice(s,
    [ap(one_op, cls) for cls in all_binops])

def one_op(s: PS, cls: type[BinOp]) -> type[BinOp]:
  '''Parse the symbol of the given binary operator and
  return its class.'''
  lit(s, cls.symbol)
  return cls

def paren_expr(s: PS) -> Expr:
  '''Parse an expression in parens.'''
  lit(s, '(')
  expr: Expr = parse_expr(s)
  space(s)
  lit(s, ')')
  return expr

def num_expr(s: PS) -> Num:
  '''Parse a number.'''
  int_part: str = ''
  frac_part: str = ''
  exp_part: str = ''
  try:
    int_part = digit1(s)
  except NoParse:
    pass
  try:
    frac_part = lit(s, '.')
    frac_part += digit1(s)
  except:
    pass
  if len(int_part) + len(frac_part) == 0:
    fail(s,
      expected=f'number',
      found=s._input[s.context.cursor:])
  try:
    exp_part = attempt(s, exponent)
  except NoParse:
    pass
  num_str: str = int_part + frac_part + exp_part
  try:
    return Num(float(num_str))
  except ValueError:
    fail(s, expected=f'number', found=num_str)

def exponent(s: PS) -> str:
  '''Parse the exponent part of a numetic litetal.'''
  exp_part: str = lit_ci(s, 'E')
  try:
    exp_part += choice(s,
      [ap(lit, sgn) for sgn in '+-'])
  except NoParse:
    pass
  exp_part += digit1(s)
  return exp_part

def func_expr(s: PS) -> Func:
  '''Parse a function call.'''
  func_cls: type[Func] = choice(s,
    [ap(one_func, func) for func in all_funcs])
  space(s)
  lit(s, '(')
  expr: Expr = parse_expr(s)
  space(s)
  lit(s, ')')
  return func_cls(expr)

def one_func(s: PS, cls: type[Func]) -> type[Func]:
  '''Parse the name of a function and return its class.'''
  lit_ci(s, cls.name)
  return cls

varname_patt: re.Pattern[str] = re.compile('[A-Z][0-9]?')
def var_expr(s: PS) -> Var:
  '''Parse a reference to a variable.'''
  name: VarName = VarName(
    regex(s, varname_patt, re.IGNORECASE)[0].upper())
  try:
    subscr: Expr = attempt(s, subscript)
    return ArrayVar(name, subscr)
  except NoParse:
    return ScalarVar(name)

def subscript(s: PS) -> Expr:
  '''Parse the subscript of an array variable.'''
  space(s)
  lit(s, '[')
  expr: Expr = parse_expr(s)
  space(s)
  lit(s, ']')
  return expr

def neg_expr(s: PS) -> Negate:
  '''Parse a negated expression.'''
  lit(s, '-')
  return Negate(non_op(s))
