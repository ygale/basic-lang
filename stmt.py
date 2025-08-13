from abc import abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum, unique
from exceptions import EvalError, RTError
from expr import (ArrayElt, ArrayVar, Expr, LookupVar,
  ScalarVar, Var, VarName)
from parse_expr import (ascii_digits1, parse_expr,
  parse_num, var_expr, var_name)
from parser import (ap, attempt, choice, end, fail, lit,
  lit_ci, many, manyNotOf, NoParse, one, optional, 
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
      addr: int = rs.line_map[self.dest]
    except KeyError:
      raise RTError(self.line_num, ' '.join([
        f'THEN destination line {self.dest}',
        f'does not exist']))
    rs.goto = addr

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
    rs.for_loops[self.var.name] = ForLoop(
      var = self.var.name,
      first_line = rs.addr + 1,
      to = self.eval_expr(rs, self.to),
      step = (1.0 if self.step is None else
        self.eval_expr(rs, self.step)))

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
    try:
      loop: ForLoop = rs.for_loops[self.var.name]
    except KeyError:
      raise RTError(self.line_num,
        f'NEXT {self.var.name} has no FOR')
    try:
      rs.scalars[self.var.name] += loop.step
    except KeyError:
      # if this happens, figure out how to catch it
      raise KeyError(' '.join([
        f'FOR variable {self.var.name} not found',
        'on line {self.line_num}']))
    if loop.step >= 0.0:
      if rs.scalars[self.var.name] <= loop.to:
        rs.goto = loop.first_line
    else:
      if rs.scalars[self.var.name] >= loop.to:
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
    print(
      str(int(val)) if val.is_integer() else str(val),
      end='')

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

def parse_printitem_sep(
    s: ParserState[str]
    ) -> tuple[PrintItem, PrintSep]:
  item: PrintItem = parse_printitem(s)
  space(s)
  sep: PrintSep = parse_printsep(s)
  return (item, sep)

@dataclass
class Print(Stmt):
  name: ClassVar[StmtName] = StmtName('PRINT')
  items: list[tuple[PrintItem, PrintSep]]
  last_item: PrintItem
  no_newline: bool
  def pprint_tokens(self) -> Iterator[str]:
    for item, sep in self.items:
      yield item.pprint_print_item(sep)
    if self.no_newline:
      yield self.last_item.pprint_print_item(
        PrintSep.SEMICOLON)
    else:
      yield self.last_item.pprint_print_item()

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    items: list[tuple[PrintItem, PrintSep]] = sepBy(s,
      space, parse_printitem_sep)
    space(s)
    last_item: PrintItem = parse_printitem(s)
    space(s)
    no_newline: bool = False
    if optional(s, ap(lit, PrintSep.SEMICOLON)
      ) is not None:
      no_newline = True
    return this(line_num,
      items, last_item, no_newline)

  def run(self, rs: RunState[Stmt]) -> None:
    item: PrintItem
    sep: PrintSep
    for item, sep in self.items:
      item.run(rs, self)
      if sep == PrintSep.COMMA:
        print(' ', end='')
    self.last_item.run(rs, self)
    if not self.no_newline:
      print()

def parse_input(s: ParserState[str]) -> float:
  '''Try hard to find a number in the input, or return
  zero.'''
  while True:
    num = optional(s, ap(attempt, parse_num))
    if num is not None:
      return num
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
    for item in self.data:
      yield str(item) + ','

  @classmethod
  def parse_body(this,
      s: ParserState[str],
      line_num: LineNum
      ) -> Self:
    return this(line_num, sepBy(s, comma, parse_num))

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

all_stmts: list[type[Stmt]] = [Let, Goto, For, Next,
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
