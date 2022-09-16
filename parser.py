from collections.abc import Generator, Sequence
from copy import copy
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import (Callable, Concatenate,
  Generic, ParamSpec, TypeVar)

# The input to a parser is a sequence of tokens.
Token = TypeVar('Token')
Output = TypeVar('Output')

P = ParamSpec('P')

@dataclass
class ParserContext:
    cursor: int = 0
    what: str | None = None

@dataclass
class ParserState(Generic[Token]):
    _input: Sequence[Token]
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
        _input: Sequence[Token],
        parser: Callable[[ParserState], Output],
        *, what: str | None = None
        ) -> Output:
    'Run the parser on the given input.'
    state = ParserState(
        _input, ParserContext(what=what))
    return parser(state)

@contextmanager
def what(s: ParserState, what: str | None
        ) -> Generator[None, None, None]:
    s.push()
    s.context.what = what
    try:
        yield
    finally:
        s.pop()

def fail(
        s: ParserState,
        expected: object,
        found: object
        ) -> None:
    '''A parser that always fails.'''
    raise NoParse(
        position=s.context.cursor,
        expected=expected,
        found=found,
        what=s.context.what)

def end(s: ParserState[object]) -> None:
    '''A parser that succeeds if there is no more
    input.'''
    if s.context.cursor < len(s._input):
        fail(s,
            expected='end of input',
            found=s._input[s.context.cursor:])

def literally(
        s: ParserState[Token],
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
        s: ParserState[Token],
        parser: Callable[
            Concatenate[ParserState[Token], P],
            Output],
        *args: P.args,
        **kwargs: P.kwargs
        ) -> Output | None:
    '''Run a parser and return None if it fails.'''
    try:
        return parser(s, *args, **kwargs)
    except NoParse:
        return None

def attempt(
        s: ParserState[Token],
        parser: Callable[
            Concatenate[ParserState[Token], P],
            Output],
        *args: P.args,
        **kwargs: P.kwargs
        ) -> Output:
    '''Run a parser, and if it fails, roll back
    ParserState to its previous state'''
    s.push()
    try:
        result = parser(s, *args, **kwargs)
    except NoParse:
        s.pop()
        raise
    s.pop()
    return result
