from basic.exceptions import RTError
from basic.run_state import LineNum, RunState
from basic.stmt import Data, End, Stmt

def run(
    prog: list[Stmt],
    first_line: LineNum | None = None
    ) -> None:
  if len(prog) == 0:
    # the empty program does nothing
    return
  rs: RunState[Stmt] = initRunState(prog, first_line)
  try:
    while True:
      rs.prog[rs.addr].run(rs)
      if rs.goto is None:
        rs.addr += 1
        # initRunState ensures that the last stmt is
        # END so we do not need to check whether addr
        # is too large
      elif type(rs.goto) == int:
        rs.addr = rs.goto
        rs.goto = None
      else: # StopRun
        return
  except RTError as e:
    print(str(e))
  except KeyboardInterrupt:
    return
  except Exception as e:
    # if this happens, figure out how to catch it
    print(f'Exception: {repr(e)}')

def initRunState(
    prog: list[Stmt],
    first_line: LineNum | None = None
    ) -> RunState[Stmt]:
  if not isinstance(prog[-1], End):
    prog.append(End(LineNum(prog[-1].line_num + 1)))
  line_map: dict[LineNum, int] = {}
  data: list[float] = []
  n: int
  stmt: Stmt
  for n, stmt in enumerate(prog):
    line_map[stmt.line_num] = n
    if isinstance(stmt, Data):
      data.extend(stmt.data)
  addr: int
  if first_line is None:
    addr = 0
  else:
    try:
      addr = line_map[first_line]
    except KeyError:
      raise RTError(first_line,
        'Starting line does not exist')
  return RunState(
    prog = prog,
    line_map = line_map,
    addr = addr,
    data = data)
