"""tre: a "token regex".  A regular pattern matching library for tokens."""
from __future__ import absolute_import
from __future__ import unicode_literals

import collections

from dumbconf._error import ParseError


def _tokens_to_src_offset(tokens, offset):
    src = ''.join(token.src for token in tokens)
    offset = sum(len(token.src) for token in tokens[:offset])
    return src, offset


def _pattern_expected_tokens(pattern):
    """Iterate the pattern and find what should have been next"""
    def _expected_inner(pattern):
        if isinstance(pattern, Pattern):
            ret = set()
            for part in pattern.sequence:
                more, done = _expected_inner(part)
                ret.update(more)
                if done:
                    return ret, True
            return ret, False
        elif isinstance(pattern, Or):
            ret = set()
            done = True
            for part in pattern.choices:
                more, part_done = _expected_inner(part)
                ret.update(more)
                done = done and part_done
            return ret, done
        elif isinstance(pattern, Star):
            return _expected_inner(pattern.pattern)[0], False
        else:
            return {pattern}, True

    possible, _ = _expected_inner(pattern)
    return tuple(sorted(possible, key=lambda cls: cls.__name__))


def pattern_expected(tokens, offset, pattern):
    expected = _pattern_expected_tokens(pattern)
    msg = 'Expected one of ({}) but received {}'.format(
        ', '.join(cls.__name__ for cls in expected),
        type(tokens[offset]).__name__,
    )
    src, offset = _tokens_to_src_offset(tokens, offset)
    raise ParseError(src, offset, msg)


class Pattern(collections.namedtuple('Pattern', ('sequence',))):
    __slots__ = ()

    def __new__(cls, *args):
        if len(args) < 2:
            raise AssertionError('Expected len(sequence) >= 2', args)
        return super(Pattern, cls).__new__(cls, args)


class Or(collections.namedtuple('Or', ('choices',))):
    __slots__ = ()

    def __new__(cls, *args):
        if len(args) < 2:
            raise AssertionError('Expected len(choices) >= 2', args)
        return super(Or, cls).__new__(cls, args)


Star = collections.namedtuple('Star', ('pattern',))


class Match(collections.namedtuple('Match', ('start', 'end', 'tokens'))):
    __slots__ = ()

    def match(self):
        return self.tokens[self.start:self.end], self.end


def matches_pattern(
    tokens, offset, pattern,
    cb=lambda tokens, offset, pattern: None,
):
    """Basically a regex language for tokens

    `cb` is called on failure and should raise or return `None`
    """
    start = offset

    if isinstance(pattern, Pattern):
        for seq in pattern.sequence:
            ret = matches_pattern(tokens, offset, seq)
            if ret is None:
                return cb(tokens, offset, seq)
            else:
                _, offset, _ = ret
        return Match(start, offset, tokens)
    elif isinstance(pattern, Or):
        for choice in pattern.choices:
            ret = matches_pattern(tokens, offset, choice)
            if ret is not None:
                return ret
        else:
            return cb(tokens, offset, pattern)
    elif isinstance(pattern, Star):
        while True:
            ret = matches_pattern(tokens, offset, pattern.pattern)
            if ret is None:
                break
            else:
                _, offset, _ = ret
        return Match(start, offset, tokens)
    elif isinstance(tokens[offset], pattern):
        return Match(start, offset + 1, tokens)
    else:
        return cb(tokens, offset, pattern)


def get_pattern(tokens, offset, pattern, single=False):
    match = matches_pattern(tokens, offset, pattern, pattern_expected)
    val, offset = match.match()
    if single:
        val, = val
    return val, offset
