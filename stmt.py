from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum, unique
from typing import ClassVar, NewType

from expr import Expr, ScalarVar, Var, VarName

LineNum = NewType('LineNum', int)
StmtName = NewType('StmtName', str)

@dataclass
class Stmt:
    name: ClassVar[StmtName]
    line_num: LineNum

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

@dataclass
class Let(Stmt):
    name = StmtName('LET')
    var: Var
    val: Expr
    def pprint_tokens(self) -> Iterator[str]:
      yield self.var.pprint()
      yield '='
      yield self.val.pprint()

@dataclass
class Goto(Stmt):
    name = StmtName('GOTO')
    dest: LineNum
    def pprint_tokens(self) -> Iterator[str]:
      yield str(self.dest)

@dataclass
class If(Stmt):
    name = StmtName('IF')
    cond: Expr
    dest: LineNum
    def pprint_tokens(self) -> Iterator[str]:
      yield self.cond.pprint()
      yield 'THEN'
      yield str(self.dest)

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

@dataclass
class Next(Stmt):
    name = StmtName('NEXT')
    var: Var
    def pprint_tokens(self) -> Iterator[str]:
      yield self.var.pprint()

@unique
class PrintSep(StrEnum):
    SEMICOLON = ';'
    COMMA = ','

@dataclass
class PrintItem:
  '''An item in a PRINT statement.'''
  def pprint(self) -> str:
    raise NotImplementedError
  def pprint_print_item(self, sep: PrintSep | None = None
                       ) -> str:
    if sep is None:
      return self.pprint()
    else:
      return self.pprint() + sep

@dataclass
class PrintNum(PrintItem):
  '''A numeric expression in a PRINT statement.'''
  val: Expr
  def pprint(self) -> str:
    return self.val.pprint()

@dataclass
class PrintString(PrintItem):
  '''A literal string in a PRINT statement.'''
  pstr: str # cannot contain a qoute char
  def pprint(self) -> str:
    return f'"{self.pstr}"'

@dataclass
class PrintChr(PrintItem):
  '''A single character specified by its Unicode value
  in a PRINT statement.'''
  chr_val: Expr
  def pprint(self) -> str:
    return f'CHR({self.chr_val.pprint()})'

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

@dataclass
class Input(Stmt):
    name = StmtName('INPUT')
    var: Var
    def pprint_tokens(self) -> Iterator[str]:
      yield self.var.pprint()

@dataclass
class Read(Stmt):
    name = StmtName('READ')
    var: Var
    def pprint_tokens(self) -> Iterator[str]:
      yield self.var.pprint()

@dataclass
class Data(Stmt):
    name = StmtName('DATA')
    data: list[float]
    def pprint_tokens(self) -> Iterator[str]:
      for item in self.data:
        yield str(item) + ','

@dataclass
class Restore(Stmt):
    name = StmtName('RESTORE')
    def pprint_tokens(self) -> Iterator[str]:
      return iter([])

@dataclass
class Dim(Stmt):
    name = StmtName('DIM')
    varname: VarName
    size: int
    def pprint_tokens(self) -> Iterator[str]:
      yield f'{self.varname}[{str(self.size)}]'

@dataclass
class Rem(Stmt):
    name = StmtName('REM')
    comment: str
    def pprint_tokens(self) -> Iterator[str]:
      yield self.comment

@dataclass
class Stop(Stmt):
    name = StmtName('STOP')
    def pprint_tokens(self) -> Iterator[str]:
      return iter([])

@dataclass
class End(Stmt):
    name = StmtName('END')
    def pprint_tokens(self) -> Iterator[str]:
      return iter([])
