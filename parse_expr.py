from expr import (ArrayVar, Expr, Num, Parens, ScalarVar,
  Var, VarName)
from func import all_funcs, Func
from op import all_binops, BinOp, Negate
from parser import (ap, attempt, choice, fail, lit,
  lit_ci, manyOf, manyOf1, oneOf, NoParse, optional,
  ParserState, space, what)

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
         found=s._input[s.cursor:])
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
           found=s._input[s.cursor:])
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

def paren_expr(s: PS) -> Parens:
  '''Parse an expression in parens.'''
  lit(s, '(')
  expr: Expr = parse_expr(s)
  space(s)
  lit(s, ')')
  return Parens(expr)

def char_range(_from: str, to: str) -> set[str]:
  '''An inclusive range of characters.'''
  return set(
    chr(i) for i in range(ord(_from), ord(to) + 1))

ascii_digit_range: set[str] = char_range('0', '9')
ascii_letter_range: set[str] = (
  char_range('A', 'Z') | char_range('a', 'z'))

def ascii_digit(s: ParserState[str]) -> str:
  '''Parse an ASCII digit.'''
  with what(s, 'ascii digit'):
    return oneOf(s, ascii_digit_range)

def ascii_digits(s: ParserState[str]) -> str:
  '''Parse zero or more ASCII digits.'''
  with what(s, 'zero or more ascii digits'):
    return manyOf(s, ascii_digit_range)

def ascii_digits1(s: ParserState[str]) -> str:
  '''Parse one or more ASCII digits.'''
  with what(s, 'one or more ascii digits'):
    return manyOf1(s, ascii_digit_range)

def ascii_letter(s: ParserState[str]) -> str:
  '''Parse an ASCII letter.'''
  with what(s, 'ascii letter'):
    return oneOf(s, ascii_letter_range)

def num_expr(s: PS) -> Num:
  '''Parse a number.'''
  int_part: str = ascii_digits(s)
  point: str = ''
  frac_part: str = ''
  exp_part: str = ''
  try:
    point = lit(s, '.')
    frac_part = ascii_digits(s)
  except NoParse:
    pass
  if len(int_part) + len(frac_part) == 0:
    fail(s,
      expected='number',
      found=s._input[s.cursor:])
  try:
    exp_part = attempt(s, exponent)
  except NoParse:
    pass
  num_str: str = ''.join([
    int_part, point, frac_part, exp_part])
  try:
    return Num(float(num_str))
  except ValueError:
    fail(s, expected='number', found=num_str)

def exponent(s: PS) -> str:
  '''Parse the exponent part of a numetic litetal.'''
  exp_part: str = lit_ci(s, 'E')
  try:
    exp_part += choice(s,
      [ap(lit, sgn) for sgn in '+-'])
  except NoParse:
    pass
  exp_part += ascii_digits1(s)
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

def var_expr(s: PS) -> Var:
  '''Parse a reference to a variable.'''
  name: VarName = VarName(ascii_letter(s).upper())
  try:
    name = VarName(name + ascii_digit(s))
  except NoParse:
    pass
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
