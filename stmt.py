from abc import abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum, unique
from exceptions import EvalError, RTError
from expr import (ArrayElt, ArrayVar, Expr, LookupVar,
  pprint_float, ScalarVar, Var, VarName)
from parse_expr import (ascii_digit_range, ascii_digits1,
  parse_expr, parse_num, var_expr, var_name)
from parser import (ap, attempt, choice, end, fail, lit,
  lit_ci, many, manyNotOf, manyOf, NoParse, one, optional, 
  ParserState, sepBy, space, the_rest)
import readline
from run_state import (ForLoop, LineNum, RunState,
  StopRun)
from typing import ClassVar, NewType, Self

StmtName = NewType('StmtName', str)

@dataclass
class Stmt:
  name: ClassVar[StmtName]
  line_num: LineNum

  @abstractmethod
  def pprint_tokens(self) -> Iterator[str]:
    '''Space-sepatated tokens for pretty-printing the
    statement. The line number and statement name are
    not included.'''
    raise NotImplementedError

  def pprint(self) -> str:
    '''Pretty-print.'''
    return ' '.join([
      str(self.line_num),
      self.name
      ] + [t for t in self.pprint_tokens()])

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    '''Parse the part of a statement following the
    line number and statement name. Then, given
    the line number, return the statement object.'''
    raise NotImplementedError

  @classmethod
  def parse(this, s: ParserState[str]) -> Self:
    '''Parse this statement from a line of text.'''
    space(s)
    line_num: LineNum = parse_linenum(s)
    space(s)
    lit_ci(s, this.name)
    space(s)
    return this.parse_body(s, line_num)

  def eval_expr(
      self,
      lv: LookupVar,
      expr: Expr
      ) -> float:
    try:
      return expr.evaluate(lv)
    except EvalError as e:
      raise RTError(self.line_num, str(e))
    except Exception as e:
      # if this happens, figure out how to catch it
      raise RTError(self.line_num,
        f'expression: {repr(e)}')

  @abstractmethod
  def run(self, rs: RunState['Stmt']) -> None:
    raise NotImplementedError

def assign(
    stmt: Stmt,
    rs: RunState[Stmt],
    var: Var,
    val: float | Expr
    ) -> None:
  '''Assign a value to a scalar or array variable.'''
  computed: float
  if type(val) == float:
    computed = val
  elif isinstance(val, Expr):
    computed = stmt.eval_expr(rs, val)
  if isinstance(var, ScalarVar):
    rs.scalars[var.name] = computed
  elif isinstance(var, ArrayVar):
    rs.set_array_elt(
      ArrayElt(
        var.name,
        stmt.eval_expr(rs, var.subscr)),
      computed)
  else:
    # if this happens, find out how to catch it
    raise TypeError(
      f'unkown var type in line {stmt.line_num}')

@dataclass
class Let(Stmt):
  name: ClassVar[StmtName] = StmtName('LET')
  var: Var
  val: Expr
  def pprint_tokens(self) -> Iterator[str]:
    yield self.var.pprint()
    yield '='
    yield self.val.pprint()

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    var: Var = var_expr(s)
    space(s)
    lit(s, '=')
    space(s)
    expr: Expr = parse_expr(s)
    return this(line_num, var, expr)

  def run(self, rs: RunState[Stmt]) -> None:
    assign(self, rs, self.var, self.val)

@dataclass
class Goto(Stmt):
  name: ClassVar[StmtName] = StmtName('GOTO')
  dest: LineNum
  def pprint_tokens(self) -> Iterator[str]:
    yield str(self.dest)

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num, parse_linenum(s))

  def run(self, rs: RunState[Stmt]) -> None:
    try:
      addr: int = rs.line_map[self.dest]
    except KeyError:
      raise RTError(self.line_num, ' '.join([
        f'GOTO destination line {self.dest}',
        f'does not exist']))
    rs.goto = addr

@dataclass
class If(Stmt):
  name: ClassVar[StmtName] = StmtName('IF')
  cond: Expr
  dest: LineNum
  def pprint_tokens(self) -> Iterator[str]:
    yield self.cond.pprint()
    yield 'THEN'
    yield str(self.dest)

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    cond: Expr = parse_expr(s)
    space(s)
    lit_ci(s, 'THEN')
    space(s)
    dest: LineNum = parse_linenum(s)
    return this(line_num, cond, dest)

  def run(self, rs: RunState[Stmt]) -> None:
    if self.eval_expr(rs, self.cond) == 0.0:
      return
    try:
      rs.goto = rs.line_map[self.dest]
    except KeyError:
      raise RTError(self.line_num, ' '.join([
        f'THEN destination line {self.dest}',
        f'does not exist']))

def parse_step(s: ParserState[str]) -> Expr:
  '''Parse the STEP clause of a FOR statement.'''
  space(s)
  lit_ci(s, 'STEP')
  space(s)
  return parse_expr(s)

@dataclass
class For(Stmt):
  name: ClassVar[StmtName] = StmtName('FOR')
  var: ScalarVar
  from_: Expr
  to: Expr
  step: Expr | None = None
  def pprint_tokens(self) -> Iterator[str]:
    yield self.var.pprint()
    yield '='
    yield self.from_.pprint()
    yield 'TO'
    yield self.to.pprint()
    if self.step is not None:
      yield 'STEP'
      yield self.step.pprint()

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    var: ScalarVar = scalar_var(s)
    space(s)
    lit(s, '=')
    space(s)
    from_: Expr = parse_expr(s)
    space(s)
    lit_ci(s, 'TO')
    space(s)
    to: Expr = parse_expr(s)
    step: Expr | None = optional(s, parse_step)
    return this(line_num, var, from_, to, step)

  def run(self, rs: RunState[Stmt]) -> None:
    rs.scalars[self.var.name] = self.eval_expr(
      rs, self.from_)
    parent: VarName | None
    if self.var.name in rs.for_loops:
      # A FOR loop for this variable is already active.
      # Cancel all nested loops before restarting it.
      inner: VarName | None = rs.inner_for
      while inner is not None:
        if inner == self.var.name:
          break
        rs.inner_for = rs.for_loops[inner].parent
        del rs.for_loops[inner]
        inner = rs.inner_for
      parent = rs.for_loops[self.var.name].parent
    else:
      parent = rs.inner_for
      rs.inner_for = self.var.name
    rs.for_loops[self.var.name] = ForLoop(
      var = self.var.name,
      first_line = rs.addr + 1,
      to = self.eval_expr(rs, self.to),
      step = (1.0 if self.step is None else
        self.eval_expr(rs, self.step)),
      parent = parent)

@dataclass
class Next(Stmt):
  name: ClassVar[StmtName] = StmtName('NEXT')
  var: ScalarVar
  def pprint_tokens(self) -> Iterator[str]:
    yield self.var.pprint()

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num, scalar_var(s))

  def run(self, rs: RunState[Stmt]) -> None:
    # cancel any nested loops and get the ForLoop
    loop: ForLoop
    while rs.inner_for is not None:
      try:
        loop = rs.for_loops[rs.inner_for]
      except KeyError:
        # if this happens, figure out how to catch it
        raise KeyError(' '.join([
          f'FOR variable {self.var.name} not found',
          'on line {self.line_num}']))
      if loop.var == self.var.name:
        break
      rs.inner_for = loop.parent
      del rs.for_loops[loop.var]
    else:
      raise RTError(self.line_num,
        f'NEXT {self.var.name} has no FOR')
    # bump the FOR variable to its next value
    try:
      rs.scalars[loop.var] += loop.step
    except KeyError:
      # if this happens, figure out how to catch it
      raise KeyError(' '.join([
        f'FOR variable {loop.var} not found',
        'on line {self.line_num}']))
    # check if the loop is done
    done: bool = (
      rs.scalars[loop.var] > loop.to
      if loop.step >= 0.0 else
      rs.scalars[loop.var] < loop.to)
    if done:
      rs.inner_for = loop.parent
      del rs.for_loops[loop.var]
    else:
      rs.goto = loop.first_line

@unique
class PrintSep(StrEnum):
  SEMICOLON = ';'
  COMMA = ','

def parse_printsep(s: ParserState[str]) -> PrintSep:
  if optional(s, ap(lit, PrintSep.SEMICOLON)
     ) is not None:
    return PrintSep.SEMICOLON
  if optional(s, ap(lit, PrintSep.COMMA)
     ) is not None:
    return PrintSep.COMMA
  fail(s,
    expected='comma or semicolon',
    found=s._input[s.cursor:])

@dataclass
class PrintItem:
  '''An item in a PRINT statement.'''

  @abstractmethod
  def pprint(self) -> str:
    raise NotImplementedError

  def pprint_print_item(self,
      sep: PrintSep | None = None
      ) -> str:
    if sep is None:
      return self.pprint()
    else:
      return self.pprint() + sep

  @classmethod
  def parse(this, s: ParserState[str]) -> Self:
    raise NotImplementedError

  @abstractmethod
  def run(self, rs: RunState[Stmt], pr: 'Print'
      ) -> None:
    raise NotImplementedError

@dataclass
class PrintNum(PrintItem):
  '''A numeric expression in a PRINT statement.'''
  val: Expr

  def pprint(self) -> str:
    return self.val.pprint()

  @classmethod
  def parse(this, s: ParserState[str]) -> Self:
    return this(parse_expr(s))

  def run(self, rs: RunState[Stmt], pr: 'Print'
      ) -> None:
    val: float = pr.eval_expr(rs, self.val)
    print(pprint_float(val), end='')

@dataclass
class PrintString(PrintItem):
  '''A literal string in a PRINT statement.'''
  pstr: str # cannot contain a double qoute

  def pprint(self) -> str:
    return f'"{self.pstr}"'

  @classmethod
  def parse(this, s: ParserState[str]) -> Self:
    lit(s, '"')
    pstr: str = manyNotOf(s, '"')
    lit(s, '"')
    return this(pstr)

  def run(self, rs: RunState[Stmt], pr: 'Print'
      ) -> None:
    print(self.pstr, end='')

@dataclass
class PrintChr(PrintItem):
  '''A single character specified by its Unicode value
  in a PRINT statement.'''
  chr_val: Expr

  def pprint(self) -> str:
    return f'CHR({self.chr_val.pprint()})'

  @classmethod
  def parse(this, s: ParserState[str]) -> Self:
    lit_ci(s, 'CHR')
    space(s)
    lit(s, '(')
    chr_val: Expr = parse_expr(s)
    space(s)
    lit(s, ')')
    return this(chr_val)

  def run(self, rs: RunState[Stmt], pr: 'Print'
      ) -> None:
    ch: float = pr.eval_expr(rs, self.chr_val)
    try:
      print(chr(int(ch)), end='')
    except ValueError:
      raise RTError(pr.line_num, ' '.join([
        f'{ch} is not a valid',
        'Unicode code point for CHR']))

def parse_printitem(s: ParserState[str]) -> PrintItem:
  return choice(
    s,
    [item for item in
      [ PrintString.parse,
        PrintChr.parse,
        PrintNum.parse] # order matters
    ]
  )

def parse_sep_printitem(
    s: ParserState[str]
    ) -> tuple[PrintSep, PrintItem]:
  sep: PrintSep = parse_printsep(s)
  space(s)
  item: PrintItem = parse_printitem(s)
  return (sep, item)

@dataclass
class PrintItems:
  '''A non-empty list of print items.'''
  first_item: PrintItem
  items: list[tuple[PrintSep, PrintItem]]
  no_newline: bool
  def pprint_tokens(self) -> Iterator[str]:
    if len(self.items) == 0:
      if self.no_newline:
        yield self.first_item.pprint_print_item(
          PrintSep.SEMICOLON)
      else:
        yield self.first_item.pprint_print_item()
    else:
      yield self.first_item.pprint_print_item(
        self.items[0][0])
      i: int
      for i in range(1, len(self.items)):
        yield self.items[i-1][1].pprint_print_item(
          self.items[i][0])
      if self.no_newline:
        yield self.items[-1][1].pprint_print_item(
          PrintSep.SEMICOLON)
      else:
        yield self.items[-1][1].pprint_print_item()

  @classmethod
  def parse(this, s: ParserState[str]) -> Self:
    first_item: PrintItem = parse_printitem(s)
    items: list[tuple[PrintSep, PrintItem]] = sepBy(s,
      space, parse_sep_printitem)
    space(s)
    no_newline: bool = False
    if optional(s, ap(lit, PrintSep.SEMICOLON)
      ) is not None:
      no_newline = True
    return this(first_item, items, no_newline)

  def run(self, rs: RunState[Stmt], pr: 'Print') -> None:
    sep: PrintSep
    item: PrintItem
    self.first_item.run(rs, pr)
    for sep, item in self.items:
      if sep == PrintSep.COMMA:
        print(' ', end='')
      item.run(rs, pr)
    if not self.no_newline:
      print()

@dataclass
class Print(Stmt):
  name: ClassVar[StmtName] = StmtName('PRINT')
  items: PrintItems | None
  def pprint_tokens(self) -> Iterator[str]:
    if self.items is not None:
      yield from self.items.pprint_tokens()

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num, optional(s, PrintItems.parse))

  def run(self, rs: RunState[Stmt]) -> None:
    if self.items is None:
      print()
    else:
      self.items.run(rs, self)

sgn_chars: set[str] = set('+-')
num_chars: set[str] = ascii_digit_range | sgn_chars | set('.')
def parse_input(s: ParserState[str]) -> float:
  '''Try hard to find a number in the input, or return
  zero.'''
  neg: bool
  num: float
  while True:
    manyNotOf(s, num_chars)
    neg = manyOf(s, sgn_chars)[-1:] == '-'
    space(s)
    try:
      num = attempt(s, parse_num)
      return -num if neg else num
    except NoParse:
      pass
    try:
      one(s)
    except NoParse:
      return 0.0

@dataclass
class Input(Stmt):
  name: ClassVar[StmtName] = StmtName('INPUT')
  var: Var
  def pprint_tokens(self) -> Iterator[str]:
    yield self.var.pprint()

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num, var_expr(s))

  def run(self, rs: RunState[Stmt]) -> None:
    try:
      inp: str = input('? ')
    except EOFError:
      assign(self, rs, self.var, 0.0)
      return
    assign(self, rs, self.var,
      parse_input(ParserState(inp)))

@dataclass
class Read(Stmt):
  name: ClassVar[StmtName] = StmtName('READ')
  var: Var
  def pprint_tokens(self) -> Iterator[str]:
    yield self.var.pprint()

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num, var_expr(s))

  def run(self, rs: RunState[Stmt]) -> None:
    if len(rs.data) == 0:
      raise RTError(self.line_num,
        'READ with no DATA.')
    if rs.data_cursor >= len(rs.data):
      raise RTError(self.line_num,
        'no more DATA for READ.')
    assign(self, rs, self.var, rs.data[rs.data_cursor])
    rs.data_cursor += 1

@dataclass
class Data(Stmt):
  name: ClassVar[StmtName] = StmtName('DATA')
  data: list[float]
  def pprint_tokens(self) -> Iterator[str]:
    for item in self.data[:-1]:
      yield pprint_float(item) + ','
    if len(self.data) > 0:
      yield pprint_float(self.data[-1])

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    data: list[float] = sepBy(s, comma, parse_num)
    if len(data) == 0:
      fail(s,
        expected = 'one or more numbers',
        found = 'none')
    return this(line_num, data)

  def run(self, rs: RunState[Stmt]) -> None:
    # data is set at startup
    return

def comma(s: ParserState[str]) -> str:
  '''Parse a comma surrounded by optional
  whitespace.'''
  space(s)
  lit(s, ',')
  space(s)
  return ','

@dataclass
class Restore(Stmt):
  name: ClassVar[StmtName] = StmtName('RESTORE')
  def pprint_tokens(self) -> Iterator[str]:
    return iter([])

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num)

  def run(self, rs: RunState[Stmt]) -> None:
    rs.data_cursor = 0

@dataclass
class Dim(Stmt):
  name: ClassVar[StmtName] = StmtName('DIM')
  varname: VarName
  size: int
  def pprint_tokens(self) -> Iterator[str]:
    yield f'{self.varname}[{str(self.size)}]'

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    varname: VarName = var_name(s)
    space(s)
    lit(s, '[')
    space(s)
    size: int = parse_natnum(s)
    space(s)
    lit(s, ']')
    return this(line_num, varname, size)

  def run(self, rs: RunState[Stmt]) -> None:
    if self.varname in rs.arrays:
      raise RTError(self.line_num,
        f'array {self.varname} already has DIM')
    rs.arrays[self.varname] = [None] * self.size

@dataclass
class Rem(Stmt):
  name: ClassVar[StmtName] = StmtName('REM')
  comment: str
  def pprint_tokens(self) -> Iterator[str]:
    yield self.comment

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num, the_rest(s))

  def run(self, rs: RunState[Stmt]) -> None:
    return

@dataclass
class Stop(Stmt):
  name: ClassVar[StmtName] = StmtName('STOP')
  def pprint_tokens(self) -> Iterator[str]:
    return iter([])

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num)

  def run(self, rs: RunState[Stmt]) -> None:
    print(f'Stopped at line {self.line_num}')
    rs.goto = StopRun()

@dataclass
class End(Stmt):
  name: ClassVar[StmtName] = StmtName('END')
  def pprint_tokens(self) -> Iterator[str]:
    return iter([])

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num)

  def run(self, rs: RunState[Stmt]) -> None:
    rs.goto = StopRun()

all_stmts: list[type[Stmt]] = [Let, Goto, If, For, Next,
  Print, Input, Read, Data, Restore, Dim, Rem, Stop,
  End]

def parse_stmt(s: ParserState[str]) -> Stmt:
  '''Parse a statement from a line of text.'''
  try:
    stmt: Stmt = choice(s,
      [stmt.parse for stmt in all_stmts])
  except NoParse:
    fail(s,
      expected='statement',
      found=s._input[s.cursor:])
  space(s)
  end(s)
  return stmt

def parse_natnum(s: ParserState[str]) -> int:
  '''Parse a positive integer.'''
  num: int = int(ascii_digits1(s))
  if num < 1:
    fail(s,
      expected='whole number',
      found=s._input[s.cursor:])
  return num

def parse_linenum(s: ParserState[str]) -> LineNum:
  '''Parse a line number.'''
  try:
    return(LineNum(parse_natnum(s)))
  except NoParse:
    fail(s,
      expected='line number',
      found=s._input[s.cursor:])

def scalar_var(s: ParserState[str]) -> ScalarVar:
  '''Parse a scalar variable reference.'''
  return ScalarVar(var_name(s))
