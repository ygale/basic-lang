from collections.abc import (Callable, Generator,
  Iterable, Sequence)
from copy import copy
from contextlib import contextmanager
from dataclasses import dataclass, field
import re
from typing import Concatenate, NoReturn, ParamSpec

@dataclass
class ParserState[Input]:
    _input: Input
    cursor: int = 0
    what: str | None = None
    cursor_stack: list[int] = field(
        default_factory=list)
    what_stack: list[str | None] = field(
        default_factory=list)

@dataclass
class NoParse(Exception):
    'A parser failed.'
    expected: object
    found: object
    position: int
    what: str | None = None

    def __post_init__(self) -> None:
        super().__init__(
            ('' if self.what is None else
                f'invalid {self.what} ') +
            f'at position {self.position}: ' +
            f'expected {self.expected} ' +
            f'found {self.found}')

def parse_with_state[Input, Output](
        _input: Input,
        parser: Callable[[ParserState[Input]], Output],
        *,
        what: str | None = None
        ) -> tuple[Output, ParserState[Input]]:
    '''Run the parser on the given input. Return the output
    and the final state.'''
    state: ParserState[Input] = ParserState(
        _input, what=what)
    try:
      return (parser(state), state)
    except NoParse as e:
        if state.what is not None:
            e.what = state.what
        raise e

def parse[Token, Output](
        _input: Sequence[Token],
        parser: Callable[
          [ParserState[Sequence[Token]]],
          Output],
        *,
        what: str | None = None
        ) -> Output:
    '''Run the parser on the given input.'''
    outp: Output
    state: ParserState[Sequence[Token]]
    outp, state = parse_with_state(
      _input, parser, what=what)
    end(state)
    return outp

def parse_initial[Token, Output](
        _input: Sequence[Token],
        parser: Callable[
          [ParserState[Sequence[Token]]],
          Output],
        *,
        what: str | None = None
        ) -> tuple[Output, Sequence[Token]]:
    '''Run the parser on the initial portion of the given
    input. Return the output and the leftover input.'''
    outp: Output
    state: ParserState[Sequence[Token]]
    outp, state = parse_with_state(
      _input, parser, what=what)
    return (outp, state._input[state.cursor:])

def ap[Input, Output, **P](
      parser: Callable[
          Concatenate[ParserState[Input], P],
          Output],
      *args: P.args,
      **kwargs: P.kwargs
      ) -> Callable[[ParserState[Input]], Output]:
    '''Convert a parser with parameters into a
    simple parser by applying all parameters
    except the first.'''
    def inner_parser(s: ParserState[Input]) -> Output:
        return parser(s, *args, **kwargs)
    return inner_parser

@contextmanager
def what(s: ParserState, what: str | None
        ) -> Generator[None]:
    s.what_stack.append(s.what)
    s.what = what
    try:
        yield
    except NoParse as e:
        fail(s,
            expected=
                what if what is not None
                     else e.expected,
            found=e.found)
    finally:
        s.what = s.what_stack[-1]
        s.what_stack.pop()

def succeed[Output](_s: object, result: Output) -> Output:
    '''A parser that always succeeds with the given
    result.'''
    return result

def fail(
        s: ParserState,
        expected: object,
        found: object,
        what: str | None = None
        ) -> NoReturn:
    '''A parser that always fails.'''
    raise NoParse(
        position=s.cursor,
        expected=expected,
        found=found,
        what=s.what if what is None else what
        ) from None

def one[Token](
      s: ParserState[Sequence[Token]]
      ) -> Token:
    '''Parse any single token.'''
    if s.cursor >= len(s._input):
        fail(s,
            expected='anything',
            found='end of input')
    tok: Token = s._input[s.cursor]
    s.cursor += 1
    return tok

def oneOf[Token](
      s: ParserState[Sequence[Token]],
      given: Iterable[Token]
      ) -> Token:
    '''Parse one of the given tokens.'''
    if s.cursor >= len(s._input):
        givens1: str = ', '.join(
          str(g) for g in given)
        fail(s,
            expected='one of {givens1}',
            found='end of input')
    tok: Token = s._input[s.cursor]
    if tok not in given:
        givens2: str = ', '.join(
          str(g) for g in given)
        fail(s,
            expected='one of {givens2}',
            found='something else')
    s.cursor += 1
    return tok

def manyOf(
      s: ParserState[str],
      given: Iterable[str]
      ) -> str:
    '''Parse zero or more of the given characters.'''
    cursor: int = s.cursor
    while (cursor < len(s._input) and
          s._input[cursor] in given):
        cursor += 1
    cursor, s.cursor = s.cursor, cursor
    return s._input[cursor:s.cursor]

def manyNotOf(
      s: ParserState[str],
      given: Iterable[str]
      ) -> str:
    '''Parse zero or more characters other than the
    given ones.'''
    cursor: int = s.cursor
    while (cursor < len(s._input) and
          s._input[cursor] not in given):
        cursor += 1
    cursor, s.cursor = s.cursor, cursor
    return s._input[cursor:s.cursor]

def manyOf1(
      s: ParserState[str],
      given: Iterable[str]
      ) -> str:
    '''Parse one or more of the given characters.'''
    cursor: int = s.cursor
    while (cursor < len(s._input) and
          s._input[cursor] in given):
        cursor += 1
    if cursor == s.cursor:
        givens: str = ', '.join(
        str(g) for g in given)
        fail(s,
            expected='at least one of {givens}',
            found='none')
    cursor, s.cursor = s.cursor, cursor
    return s._input[cursor:s.cursor]

def the_rest[Token](s: ParserState[Sequence[Token]]
      ) -> Sequence[Token]:
    '''Consume all of the remaining input.'''
    rest: Sequence[Token] = s._input[s.cursor:]
    s.cursor = len(s._input)
    return rest

def end[Input: Sequence](s: ParserState[Input]) -> None:
    '''A parser that succeeds if there is no more
    input.'''
    if s.cursor < len(s._input):
        fail(s,
            expected='end of input',
            found=s._input[s.cursor:])

def satisfy[Token](
      s: ParserState[Sequence[Token]],
      pred: Callable[[Token], bool]
      ) -> Token:
    '''Parse a single token that satisfies the
    given predicate.'''
    try:
        tok: Token = s._input[s.cursor]
    except IndexError:
        fail(s,
            expected=f'satisfies {str(pred)}',
            found='end of input')
    if not pred(tok):
        fail(s,
            expected=f'satisfies {str(pred)}',
            found=tok)
    s.cursor += 1
    return tok

def lit[Input: (str, bytes)](
      s: ParserState[Input],
      given: Input
      ) -> Input:
    '''Parse and consume the given sequence of tokens.
    If the parse fails, no input is consumed.'''
    prefix: Input = s._input[
        s.cursor:
        s.cursor + len(given)]
    if prefix != given:
        fail(s,
            expected = given,
            found = prefix)
    s.cursor += len(given)
    return prefix

def optional[Input, Output](
      s: ParserState[Input],
      parser: Callable[[ParserState[Input]], Output]
      ) -> Output | None:
    '''Run a parser and return None if it fails.'''
    try:
        return parser(s)
    except NoParse:
        return None

def attempt[Input, Output](
      s: ParserState[Input],
      parser: Callable[[ParserState[Input]], Output]
      ) -> Output:
    '''Run a parser, and if it fails, roll back
    ParserState to its previous state'''
    s.cursor_stack.append(s.cursor)
    try:
        return parser(s)
    except NoParse:
        s.cursor = s.cursor_stack[-1]
        raise
    finally:
        s.cursor_stack.pop()

def choice[Input, Output](
      s: ParserState[Input],
      parsers: Iterable[
        Callable[[ParserState[Input]], Output]]
      ) -> Output:
    '''Return the result of the first parser that
    succeeds.'''
    expects: list[object] = []
    found1: object = None
    for parser in parsers:
        try:
            return attempt(s, parser)
        except NoParse as e:
            expects.append(e.expected)
            if found1 is None:
                found1 = e.found
    fail(s,
         expected=
            ' or '.join([str(ex) for ex in expects])
            if len(expects) > 0 else 'no choices',
         found=found1)

def many[Input, Output](
      s: ParserState[Input],
      parser: Callable[[ParserState[Input]], Output]
      ) -> list[Output]:
    '''Run a parser as many times as it succeeds,
    and collect the outputs in a list.'''
    res: list[Output] = []
    while True:
        try:
            res.append(parser(s))
        except NoParse:
            return res

def sepBy[Input, Output](
      s: ParserState[Input],
      sep: Callable[[ParserState[Input]], object],
      parser: Callable[[ParserState[Input]], Output]
      ) -> list[Output]:
    '''Zero or more occurrences of parser separated by
    sep. The separators are not included in the
    output.'''
    try:
        res: list[Output] = [parser(s)]
    except NoParse:
        return []
    while True:
        try:
            res.append(
              attempt(s,
                ap(parse_tuple, sep, parser)
              )[1]
            )
        except NoParse:
            return res

def parse_tuple[Input, Output0, Output1](
      s: ParserState[Input],
      parser0: Callable[[ParserState[Input]], Output0],
      parser1: Callable[[ParserState[Input]], Output1]
      ) -> tuple[Output0, Output1]:
    '''Run two parsers and return their outputs as a
    tuple'''
    return (parser0(s), parser1(s))

def many1[Input, Output](
      s: ParserState[Input],
      parser: Callable[[ParserState[Input]], Output]
      ) -> list[Output]:
    '''Run a parser at least once, and as many more
    times after that as it succeeds,
    and collect the outputs in a list.'''
    res: list[Output] = [parser(s)]
    res += many(s, parser)
    return res

def regex[T: (str, bytes)](
        s: ParserState[T],
        patt: re.Pattern[T]
        ) -> tuple[T, list[T]]:
    '''Parse the given compiled regex. Return the matched
    string and the group matches. No input is consumed if
    the regex does not match.'''
    start: int = s.cursor
    m_optional: re.Match[T] | None = patt.match(
        s._input[start:])
    if m_optional is None:
        fail(s,
             expected=patt.pattern,
             found=s._input[start:])
    else:
        m: re.Match[T] = m_optional
    s.cursor += m.end()
    return (
        s._input[start:start+m.end()],
        [g for g in m.groups()])

def lit_ci[T: (str, bytes)](
        s: ParserState[T],
        given: T
        ) -> T:
    '''Parse and consume the given case insensitive string.
    If the parse fails, no input is consumed.'''
    return regex(s,
      re.compile(re.escape(given), re.IGNORECASE)
      )[0]

space_patt: re.Pattern[str] = re.compile(r'\s*')
bspace_patt: re.Pattern[bytes] = re.compile(b'\\s*')
def space[T: (str, bytes)](s: ParserState[T]) -> T:
    '''Parse optional whitespace.'''
    if isinstance(s._input, str):
        return regex(s, space_patt)[0]
    else:
        return regex(s, bspace_patt)[0]

space1_patt: re.Pattern[str] = re.compile(r'\s+')
bspace1_patt: re.Pattern[bytes] = re.compile(b'\\s+')
def space1[T: (str, bytes)](s: ParserState[T]) -> T:
    '''Parse whitespace.'''
    try:
        if isinstance(s._input, str):
            return regex(s, space1_patt)[0]
        else:
            return regex(s, bspace1_patt)[0]
    except NoParse as e:
        fail(s,
            expected='whitespace',
            found=e.found)

digit1_patt: re.Pattern[str] = re.compile(r'[0-9]+')
bdigit1_patt: re.Pattern[bytes] = re.compile(b'[0-9]+')
def digit1[T: (str, bytes)](s: ParserState[T]) -> T:
    '''Parse one or more digits.'''
    try:
        if isinstance(s._input, str):
            return regex(s, digit1_patt)[0]
        else:
            return regex(s, bdigit1_patt)[0]
    except NoParse as e:
        fail(s,
            expected='one or more digits',
            found=e.found)
