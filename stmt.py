from dataclasses import dataclass
from enum import Enum, unique
from typing import ClassVar, NewType

from expr import Expr, Var, VarName

LineNum = NewType('LineNum', int)
StmtName = NewType('StmtName', str)

@dataclass(frozen=True)
class Stmt:
    name: ClassVar[StmtName]
    line_num: LineNum

@dataclass(frozen=True)
class Let(Stmt):
    name = StmtName('LET')
    var: Var
    val: Expr

@dataclass(frozen=True)
class Goto(Stmt):
    name = StmtName('GOTO')
    dest: LineNum

@dataclass(frozen=True)
class If(Stmt):
    name = StmtName('IF')
    cond: Expr
    dest: LineNum

class For(Stmt):
    name = StmtName('FOR')
    var: Var
    from_: Expr
    to: Expr
    step: Expr | None

@dataclass(frozen=True)
class Next(Stmt):
    name = StmtName('NEXT')
    var: Var

PrintNum = Expr
PrintString = str
PrintChr = Expr
PrintItem = PrintNum | PrintString | PrintChr

@unique
class PrintSep(Enum):
    SEMICOLON = ';'
    COMMA = ','

@dataclass(frozen=True)
class Print(Stmt):
    name = StmtName('PRINT')
    items: list[tuple[PrintItem, PrintSep]]
    last_item: PrintItem
    no_newline: bool

@dataclass(frozen=True)
class Input(Stmt):
    name = StmtName('INPUT')
    var: Var

@dataclass(frozen=True)
class Read(Stmt):
    name = StmtName('READ')
    var: Var

@dataclass(frozen=True)
class Data(Stmt):
    name = StmtName('DATA')
    data: list[float]

@dataclass(frozen=True)
class Dim(Stmt):
    name = StmtName('DIM')
    varname: VarName
    size: int

@dataclass(frozen=True)
class Rem(Stmt):
    name = StmtName('REM')
    comment: str

@dataclass(frozen=True)
class End(Stmt):
    name = StmtName('END')
