from dataclasses import dataclass
from typing import ClassVar

@dataclass
class RTError(Exception):
  line: int
  msg: str

  def __str__(self) -> str:
    return f'Error on line {self.line}: {self.msg}'

@dataclass
class BaseReplError(Exception):
  error_type: ClassVar[str]
  msg: str
  line: int | None = None

  def __str__(self) -> str:
    line_msg: str = (
      '' if self.line is None else f' on line {self.line}')
    return f'{self.error_type}{line_msg}: {self.msg}'

@dataclass
class ReplError(BaseReplError):
  error_type = 'Error'

@dataclass
class ReplSyntaxError(BaseReplError):
  error_type = 'Syntax error'

class EvalError(ValueError):
  pass
