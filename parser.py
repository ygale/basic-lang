from collections.abc import (Callable, Generator,
  Iterable, Sequence)
from copy import copy
from contextlib import contextmanager
from dataclasses import dataclass, field
import re
from typing import (Any, Concatenate, Generic,
  NoReturn, ParamSpec, TypeVar)

# The input to a parser is a sequence of tokens.
Token = TypeVar('Token')
Input = TypeVar('Input')
Input_co = TypeVar('Input_co', covariant=True)
Output = TypeVar('Output')

P = ParamSpec('P')

@dataclass
class ParserContext:
    cursor: int = 0
    what: str | None = None

@dataclass
class ParserState(Generic[Input_co]):
    _input: Input_co
    context: ParserContext = field(
        default_factory=ParserContext)
    stack: list[ParserContext] = field(
        default_factory=list)

    def push(self) -> None:
        '''Push the current context onto the stack.
        and create a copy of it to use as the
        current context.'''
        self.stack.append(self.context)
        self.context = copy(self.context)

    def pop(self) -> None:
        '''Pop the last previous context from the stack,
        and restore it as the new current context.'''
        try:
            self.context = self.stack[-1]
        except IndexError:
            raise ValueError(
                'Cannot pop empty ParserState stack')
        self.stack.pop() 

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

def parse(
        _input: Input,
        parser: Callable[[ParserState[Input]], Output],
        *,
        what: str | None = None
        ) -> Output:
    'Run the parser on the given input.'
    state = ParserState(
        _input, ParserContext(what=what))
    try:
        return parser(state)
    except NoParse as e:
        if state.context.what is not None:
            what = state.context.what
        else:
            what = e.what
        fail(state,
            e.expected,
            e.found,
            what)

def ap(
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
        ) -> Generator[None, None, None]:
    s.push()
    s.context.what = what
    try:
        yield
    except NoParse as e:
        fail(s,
            expected=
                what if what is not None
                     else e.expected,
            found=e.found)
    finally:
        s.pop()

def fail(
        s: ParserState,
        expected: object,
        found: object,
        what: str | None = None
        ) -> NoReturn:
    '''A parser that always fails.'''
    raise NoParse(
        position=s.context.cursor,
        expected=expected,
        found=found,
        what=s.context.what if what is None else what
        ) from None

def end(s: ParserState[Sequence]) -> None:
    '''A parser that succeeds if there is no more
    input.'''
    if s.context.cursor < len(s._input):
        fail(s,
            expected='end of input',
            found=s._input[s.context.cursor:])

def satisfy(
        s: ParserState[Sequence[Token]],
        pred: Callable[[Token], bool]
        ) -> Token:
    '''Parse a single token that satisfies the
    given predicate.'''
    tok: Token = s._input[s.context.cursor]
    if not pred(tok):
        fail(s,
            expected=f'satisfies {str(pred)}',
            found=tok)
    s.context.cursor += 1
    return tok

def lit(
        s: ParserState[Sequence[Token]],
        given: Sequence[Token]
        ) -> Sequence[Token]:
    '''Parse and consume the given sequence of tokens.
    If the parse fails, no input is consumed.'''
    prefix: Sequence[Token] = s._input[
        s.context.cursor:
        s.context.cursor + len(given)]
    if prefix != given:
        fail(s,
            expected = given,
            found = prefix)
    s.context.cursor += len(given)
    return prefix

def optional(
        s: ParserState[Input],
        parser: Callable[[ParserState[Input]], Output]
        ) -> Output | None:
    '''Run a parser and return None if it fails.'''
    try:
        return parser(s)
    except NoParse:
        return None

def attempt(
        s: ParserState[Input],
        parser: Callable[[ParserState[Input]], Output]
        ) -> Output:
    '''Run a parser, and if it fails, roll back
    ParserState to its previous state'''
    s.push()
    try:
        result = parser(s)
    except NoParse:
        s.pop()
        raise
    return result

def choice(
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
            return parser(s)
        except NoParse as e:
            expects.append(e.expected)
            if found1 is None:
                found1 = e.found
    fail(s,
         expected=
            ' or '.join([str(ex) for ex in expects])
            if len(expects) > 0 else 'no choices',
         found=found1)
    return [][0]

def many(
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

def many1(
        s: ParserState[Input],
        parser: Callable[[ParserState[Input]], Output]
        ) -> list[Output]:
    '''Run a parser at least once, and as many more
    times after that as it succeeds,
    and collect the outputs in a list.'''
    res: list[Output] = [parser(s)]
    res += many(s, parser)
    return res

def regex(
        s: ParserState[str],
        patt: re.Pattern[str],
        ) -> tuple[str, list[str]]:
    '''Parse the given compiled regex. Return
    the matched string and the group matches.:'''
    m_optional: re.Match[str] | None = patt.match(
        s._input, s.context.cursor)
    if m_optional is None:
        fail(s,
             expected=patt.pattern,
             found=s._input[s.context.cursor:])
    else:
        m: re.Match[str] = m_optional
    s.context.cursor += m.end() - m.start()
    return (
        s._input[m.start():m.end()],
        [g for g in m.groups()])

space_patt: re.Pattern[str] = re.compile(r'\s*')
def space(s: ParserState[str]) -> str:
    '''Parse optional whitespace.'''
    return regex(s, space_patt)[0]

space1_patt: re.Pattern[str] = re.compile(r'\s+')
def space1(s: ParserState[str]) -> str:
    '''Parse whitespace.'''
    try:
        return regex(s, space1_patt)[0]
    except NoParse as e:
        fail(s,
            expected='whitespace',
            found=e.found)
