from __future__ import absolute_import
from __future__ import unicode_literals

import re

from dumbconf import _primitive
from dumbconf import ast
from dumbconf._error import ParseError


def _or(*args):
    return '({})'.format('|'.join(args))


def _nor(*args):
    return ''.join('(?<!{})'.format(arg) for arg in args)


COLON_RE = re.compile(':')
COMMA_RE = re.compile(',')
COMMENT_RE = re.compile('# .*(\n|$)')
INDENT_RE = re.compile('(?<=\n)(    )+')
NL_RE = re.compile('\n')
SPACE_RE = re.compile('(?<!\n) ')

BOOL_TOKENS = ('true', 'false')
BOOL_RE = re.compile(_or(*BOOL_TOKENS))
NULL_RE = re.compile('null')
_exp = '([eE][-+]?[0-9]+)'
FLOAT_RE = re.compile('-?' + _or(
    '[0-9]+' + _exp,
    r'[0-9]+\.[0-9]*{}?'.format(_exp),
    r'\.[0-9]+{}?'.format(_exp),
))
INT_RE = re.compile('-?' + _or(
    '0x[0-9a-fA-F]+', '0b[0-1]+', '0o[0-7]+', '0', '[1-9][0-9]*',
))
STRING_RE = re.compile(_or(
    r"'[^\n'\\]*(?:\\.[^\n'\\]*)*'", r'"[^\n"\\]*(?:\\.[^\n"\\]*)*"',
))
BARE_WORD_RE = re.compile(
    '[A-Za-z_][A-Za-z0-9_-]*' +
    # Followed by some non-identifier
    '(?![A-Za-z0-9_-])' +
    # But not our bool / null tokens
    _nor(*BOOL_TOKENS) + _nor('null'),
)

LIST_START_RE = re.compile(r'\[')
LIST_END_RE = re.compile(']')

MAP_START_RE = re.compile('{')
MAP_END_RE = re.compile('}')


def _reg_parse(reg, cls, src, offset):
    match = reg.match(src, offset)
    return cls(match.group()), match.end()


def _reg_parse_val(reg, cls, to_val_func, src, offset):
    match = reg.match(src, offset)
    val = to_val_func(match.group())
    return cls(val, match.group()), match.end()


tokenize_processors = (
    (BARE_WORD_RE, _reg_parse_val, ast.BareWordKey, _primitive.BareWord.parse),
    (BOOL_RE, _reg_parse_val, ast.Bool, _primitive.Bool.parse),
    (NULL_RE, _reg_parse_val, ast.Null, _primitive.Null.parse),
    (FLOAT_RE, _reg_parse_val, ast.Float, _primitive.Float.parse),
    (INT_RE, _reg_parse_val, ast.Int, _primitive.Int.parse),
    (STRING_RE, _reg_parse_val, ast.String, _primitive.String.parse),
    (LIST_START_RE, _reg_parse, ast.ListStart),
    (LIST_END_RE, _reg_parse, ast.ListEnd),
    (MAP_START_RE, _reg_parse, ast.MapStart),
    (MAP_END_RE, _reg_parse, ast.MapEnd),
    (COLON_RE, _reg_parse, ast.Colon),
    (COMMA_RE, _reg_parse, ast.Comma),
    (COMMENT_RE, _reg_parse, ast.Comment),
    (INDENT_RE, _reg_parse, ast.Indent),
    (NL_RE, _reg_parse, ast.NL),
    (SPACE_RE, _reg_parse, ast.Space),
)


def tokenize(src, offset=0):
    srclen = len(src)
    tokens = []
    while offset < srclen:
        for processor in tokenize_processors:
            reg, func = processor[:2]
            args = processor[2:] + (src, offset)
            if reg.match(src, offset):
                token, offset = func(reg, *args)
                tokens.append(token)
                break
        else:
            raise ParseError(src, offset, 'Unexpected token')
    tokens.append(ast.EOF(''))
    return tuple(tokens)
