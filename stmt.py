from abc import abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum, unique
from expr import Expr
from parse_expr import (ascii_digits1, parse_expr,
  parse_num, var_expr, var_name)
from parser import (ap, choice, end, fail, lit, lit_ci,
  many, manyNotOf, NoParse, optional, ParserState,
  sepBy, space, the_rest)
from typing import ClassVar, NewType, Self

from expr import Expr, ScalarVar, Var, VarName

LineNum = NewType('LineNum', int)
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

    @abstractmethod
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

@dataclass
class Let(Stmt):
    name = StmtName('LET')
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

@dataclass
class Goto(Stmt):
    name = StmtName('GOTO')
    dest: LineNum
    def pprint_tokens(self) -> Iterator[str]:
      yield str(self.dest)

    @classmethod
    def parse_body(this,
        s: ParserState[str],
        line_num: LineNum
        ) -> Self:
      return this(line_num, parse_linenum(s))

@dataclass
class If(Stmt):
    name = StmtName('IF')
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

@dataclass
class For(Stmt):
    name = StmtName('FOR')
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
      to: Expr = parse_expr(s)
      space(s)
      step: Expr | None = optional(s, parse_expr)
      return this(line_num, var, from_, to, step)

@dataclass
class Next(Stmt):
    name = StmtName('NEXT')
    var: ScalarVar
    def pprint_tokens(self) -> Iterator[str]:
      yield self.var.pprint()

    @classmethod
    def parse_body(this,
        s: ParserState[str],
        line_num: LineNum
        ) -> Self:
      return this(line_num, scalar_var(s))

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

  @abstractmethod
  @classmethod
  def parse(this, s: ParserState[str]) -> Self:
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

@dataclass
class PrintString(PrintItem):
  '''A literal string in a PRINT statement.'''
  pstr: str # cannot contain a qoute, CR, or LF

  def pprint(self) -> str:
    return f'"{self.pstr}"'

  @classmethod
  def parse(this, s: ParserState[str]) -> Self:
    lit(s, '"')
    pstr: str = manyNotOf(s, '"')
    lit(s, '"')
    return this(pstr)

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
    name = StmtName('PRINT')
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

@dataclass
class Input(Stmt):
    name = StmtName('INPUT')
    var: Var
    def pprint_tokens(self) -> Iterator[str]:
      yield self.var.pprint()

    @classmethod
    def parse_body(this,
        s: ParserState[str],
        line_num: LineNum
        ) -> Self:
      return this(line_num, var_expr(s))

@dataclass
class Read(Stmt):
    name = StmtName('READ')
    var: Var
    def pprint_tokens(self) -> Iterator[str]:
      yield self.var.pprint()

    @classmethod
    def parse_body(this,
        s: ParserState[str],
        line_num: LineNum
        ) -> Self:
      return this(line_num, var_expr(s))

@dataclass
class Data(Stmt):
    name = StmtName('DATA')
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

def comma(s: ParserState[str]) -> str:
    '''Parse a comma surrounded by optional
    whitespace.'''
    space(s)
    lit(s, ',')
    space(s)
    return ','

@dataclass
class Restore(Stmt):
    name = StmtName('RESTORE')
    def pprint_tokens(self) -> Iterator[str]:
      return iter([])

    @classmethod
    def parse_body(this,
        s: ParserState[str],
        line_num: LineNum
        ) -> Self:
      return this(line_num)

@dataclass
class Dim(Stmt):
    name = StmtName('DIM')
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

@dataclass
class Rem(Stmt):
    name = StmtName('REM')
    comment: str
    def pprint_tokens(self) -> Iterator[str]:
      yield self.comment

    @classmethod
    def parse_body(this,
        s: ParserState[str],
        line_num: LineNum
        ) -> Self:
      return this(line_num, the_rest(s))

@dataclass
class Stop(Stmt):
    name = StmtName('STOP')
    def pprint_tokens(self) -> Iterator[str]:
      return iter([])

    @classmethod
    def parse_body(this,
        s: ParserState[str],
        line_num: LineNum
        ) -> Self:
      return this(line_num)

@dataclass
class End(Stmt):
    name = StmtName('END')
    def pprint_tokens(self) -> Iterator[str]:
      return iter([])

    @classmethod
    def parse_body(this,
        s: ParserState[str],
        line_num: LineNum
        ) -> Self:
      return this(line_num)

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
