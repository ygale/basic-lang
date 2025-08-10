from dataclasses import dataclass

@dataclass
class RTError(Exception):
  line: int
  msg: str

  def __str__(self) -> str:
    return f'Error on line {self.line}: {self.msg}'

class EvalError(ValueError):
  pass
