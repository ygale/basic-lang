from abc import abstractmethod
from basic.exceptions import (BaseReplError, ReplError,
  ReplSyntaxError)
from basic.run import run
from basic.run_state import LineNum
from basic.stmt import parse_linenum, parse_stmt, Stmt
from collections.abc import Iterator
from dataclasses import dataclass, field
from io import TextIOWrapper
from tdp_parser.parser import (ap, choice, end, fail, lit,
  lit_ci, NoParse, optional, parse, parse_tuple, ParserState,
  space, the_rest)
import readline
from typing import ClassVar, NewType, Self

@dataclass
class ReplState:
  prog: dict[LineNum, Stmt] = field(
    default_factory = dict)
  dirty: bool = False
  exit_repl: bool = False

@dataclass
class LineRange:
  from_: LineNum | None
  to: LineNum | None

def parse_line_range(s: ParserState[str]) -> LineRange:
  try:
    return choice(s, [
      parse_line_range_from,
      parse_line_range_to,
      ])
  except NoParse:
    return LineRange(None, None)

def parse_line_range_from(s: ParserState[str]) -> LineRange:
  from_: LineNum = parse_linenum(s)
  space(s)
  try:
    lit(s, '-')
  except NoParse:
    return LineRange(from_, from_)
  space(s)
  to: LineNum | None = optional(s, parse_linenum)
  space(s)
  return LineRange(from_, to)

def parse_line_range_to(s: ParserState[str]) -> LineRange:
  lit(s, '-')
  space(s)
  to: LineNum = parse_linenum(s)
  space(s)
  return LineRange(None, to)

CmdName = NewType('CmdName', str)

@dataclass
class Cmd:
  name: ClassVar[CmdName]

  @classmethod
  def parse_body(this, s: ParserState[str]) -> Self:
    '''Parse the part of a command following the command name.
    Return the command object.'''
    raise NotImplementedError

  @classmethod
  def parse(this, s: ParserState[str]) -> Self:
    '''Parse this command from a line of text.'''
    space(s)
    lit_ci(s, this.name)
    space(s)
    return this.parse_body(s)

  @abstractmethod
  def run(self, rs: ReplState) -> None:
    raise NotImplementedError

@dataclass
class Add(Cmd):
  '''Read program lines from a file, and merge them into the
  current program. If a line number already exists, replace
  that line with the new one.'''
  name: ClassVar[CmdName] = CmdName('ADD')
  file_name: str

  @classmethod
  def parse_body(this, s: ParserState[str]) -> Self:
    file_name: str = the_rest(s)
    return this(file_name.rstrip())

  def run(self, rs: ReplState) -> None:
    rs.prog.update((stmt.line_num, stmt)
      for stmt in read_stmts(rs, self.file_name))
    rs.dirty = True

@dataclass
class Exit(Cmd):
  '''Exit the REPL.'''
  name: ClassVar[CmdName] = CmdName('EXIT')

  @classmethod
  def parse_body(this, s: ParserState[str]) -> Self:
    return this()

  def run(self, rs: ReplState) -> None:
    if are_you_sure(rs):
      rs.exit_repl = True

@dataclass
class List(Cmd):
  '''Print the lines of the program. If a range is specified,
  only print the lines whose line number is within the
  range.'''
  name: ClassVar[CmdName] = CmdName('LIST')
  lines: LineRange

  @classmethod
  def parse_body(this, s: ParserState[str]) -> Self:
    return this(parse_line_range(s))

  def run(self, rs: ReplState) -> None:
    for stmt in list_stmts(rs, self.lines):
      print(stmt.pprint())

@dataclass
class Load(Cmd):
  '''Same as NEW and then ADD.'''
  name: ClassVar[CmdName] = CmdName('LOAD')
  file_name: str

  @classmethod
  def parse_body(this, s: ParserState[str]) -> Self:
    file_name: str = the_rest(s)
    return this(file_name.rstrip())

  def run(self, rs: ReplState) -> None:
    if are_you_sure(rs):
      rs.prog = {stmt.line_num: stmt
        for stmt in read_stmts(rs, self.file_name)}
      rs.dirty = False

@dataclass
class New(Cmd):
  '''Delete all lines of the current program.'''
  name: ClassVar[CmdName] = CmdName('NEW')

  @classmethod
  def parse_body(this, s: ParserState[str]) -> Self:
    return this()

  def run(self, rs: ReplState) -> None:
    if are_you_sure(rs):
      rs.prog = {}
      rs.dirty = False

@dataclass
class Quit(Cmd):
  '''Exit the REPL.'''
  name: ClassVar[CmdName] = CmdName('QUIT')

  @classmethod
  def parse_body(this, s: ParserState[str]) -> Self:
    return this()

  def run(self, rs: ReplState) -> None:
    if are_you_sure(rs):
      rs.exit_repl = True

@dataclass
class Run(Cmd):
  '''Run the current program.'''
  name: ClassVar[CmdName] = CmdName('RUN')
  first_line: LineNum | None

  @classmethod
  def parse_body(this, s: ParserState[str]) -> Self:
    return this(optional(s, parse_linenum))

  def run(self, rs: ReplState) -> None:
    run(list(list_stmts(rs)), self.first_line)

@dataclass
class Save(Cmd):
  '''Save the program to a file. If a range is specified,
  only save the lines whose line number is within the
  range.'''
  name: ClassVar[CmdName] = CmdName('SAVE')
  lines: LineRange
  file_name: str

  @classmethod
  def parse_body(this, s: ParserState[str]) -> Self:
    lines: LineRange = parse_line_range(s)
    space(s)
    file_name: str = the_rest(s)
    return this(lines, file_name.rstrip())

  def run(self, rs: ReplState) -> None:
    try:
      f: TextIOWrapper
      with open(self.file_name, 'w', encoding='utf-8') as f:
        for stmt in list_stmts(rs, self.lines):
          print(stmt.pprint(), file=f)
    except Exception as e:
      raise ReplError(f'Exception: {e}')
    if self.lines.from_ is None and self.lines.to is None:
      rs.dirty = False

all_cmds: list[type[Cmd]] = [Add, Exit, List, Load, New, Quit,
  Run, Save]

def parse_cmd(s: ParserState[str]) -> Cmd:
  '''Parse a command from a line of text.'''
  try:
    cmd: Cmd = choice(s,
      [cmd.parse for cmd in all_cmds])
  except NoParse:
    fail(s,
      expected='command',
      found=s._input[s.cursor:])
  space(s)
  end(s)
  return cmd

def are_you_sure(rs: ReplState) -> bool:
  '''When uders are about to lose unsaved changes, give them a
  chance to change their mind.'''
  if not rs.dirty:
    return True
  try:
    ans: str = input(
      'You have not saved your changes. Are you sure? ')
  except Exception:
    return False
  if ans.lower() in ['y', 'yes', 'yep']:
    return True
  return False

def read_stmts(
    rs: ReplState,
    file_name: str
    ) -> Iterator[Stmt]:
  '''Read statements from a file.'''
  try:
    f: TextIOWrapper
    with open(file_name, 'r', encoding='utf-8') as f:
      line: str
      for line in f:
        line = line.strip()
        try:
          yield parse_stmt(ParserState(line))
        except NoParse as e:
          raise ReplSyntaxError(str(e),
            optional(ParserState(line), parse_linenum))
  except ReplSyntaxError:
    raise
  except Exception as e:
    raise ReplError(f'Exception: {str(e)}')

def list_stmts(
    rs: ReplState,
    lines: LineRange = LineRange(None, None)
    ) -> Iterator[Stmt]:
  '''List the statements of the program within the given range
  of line numbers, in order of line number.'''
  for stmt in sorted(rs.prog.values(),
      key = lambda s: s.line_num):
    if (lines.from_ is not None
        and stmt.line_num < lines.from_):
      continue
    if (lines.to is not None and stmt.line_num > lines.to):
      break
    yield stmt

def only_linenum(s: ParserState[str]) -> LineNum:
  '''Parse an entire line that is only a line number.'''
  line_num: LineNum = parse_linenum(s)
  end(s)
  return line_num

def repl() -> None:
  '''Run the repl.'''
  rs: ReplState = ReplState()
  while True:
    try:
      inp: str = input()
    except KeyboardInterrupt:
      continue
    except EOFError:
      # user hit ctrl-d
      return
    inp = inp.strip()
    if len(inp) == 0:
      continue

    line_num: LineNum | None = optional(
      ParserState(inp), only_linenum)
    if line_num is not None:
      # just a line number, the user wants to delete it
      try:
        del rs.prog[line_num]
        rs.dirty = True
      except KeyError:
        pass
      continue

    line_num = optional(ParserState(inp), parse_linenum)
    if line_num is not None:
      # starts with a line number, it is a statement
      try:
        rs.prog[line_num] = parse_stmt(ParserState(inp))
        rs.dirty = True
      except NoParse as e:
        print(str(ReplSyntaxError(str(e), line_num)))
      continue

    # otherwise, it is a repl command
    try:
      parse_cmd(ParserState(inp)).run(rs)
    except NoParse as e:
      print(str(ReplSyntaxError(str(e))))
    except BaseReplError as e:
      print(str(e))
    except Exception as e:
      print(str(ReplError(msg=f'Exception: {str(e)}')))

    if rs.exit_repl:
      return
