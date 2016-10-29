from __future__ import absolute_import
from __future__ import unicode_literals

import ast as python_ast
import collections
import contextlib
import functools
import re


class ParseError(ValueError):
    def __init__(self, src, offset, msg=None):
        self.src = src
        self.offset = offset
        self.msg = msg

    def __str__(self):
        if not self.src:
            return self.msg
        src_to = self.src[:self.offset + 1]
        if '\n' not in src_to:
            line = 1
            col = self.offset + 1
        elif src_to.endswith('\n'):
            line = src_to.count('\n')
            col = len(src_to) - src_to[:-1].rfind('\n') - 1
        else:
            line = src_to.count('\n') + 1
            col = len(src_to) - src_to.rfind('\n') - 1

        line_index = line - 1
        lines = self.src.splitlines()
        formatted_lines = ''

        def format_line(index):
            return '{: <4}|{}\n'.format(index + 1, lines[index])

        for index in range(max(0, line_index - 2), line_index):
            formatted_lines += format_line(index)

        formatted_lines += format_line(line_index)
        formatted_lines += ' ' * (4 + col) + '^\n'

        for index in range(line_index + 1, min(len(lines), line_index + 3)):
            formatted_lines += format_line(index)

        return (
            '{}\n\n'
            'Line {}, column {}\n\n'
            'Line|Source\n'
            '----|------------------------------------------------------\n'
            '{}'.format(self.msg or '', line, col, formatted_lines)
        )


def _tokens_to_src_offset(tokens, offset):
    src = ''.join(token.src for token in tokens)
    offset = sum(len(token.src) for token in tokens[:offset])
    return src, offset


def _token_expected(tokens, offset, expected):
    expected = expected if isinstance(expected, tuple) else (expected,)
    msg = 'Expected one of ({}) but received {}'.format(
        ', '.join(cls.__name__ for cls in expected),
        type(tokens[offset]).__name__,
    )
    src, offset = _tokens_to_src_offset(tokens, offset)
    raise ParseError(src, offset, msg)


def ast_cls(*args, **kwargs):
    # TODO: add more useful things here
    return collections.namedtuple(*args, **kwargs)


class ast:
    Doc = ast_cls('Doc', ('head', 'body', 'tail'))

    YamlList = ast_cls('YamlList', ('items',))
    YamlListItem = ast_cls('YamlListItem', ('head', 'val', 'tail'))
    YamlListItemHead = ast_cls('YamlListItemHead', ('src',))

    JsonList = ast_cls('JsonList', ('head', 'items', 'tail'))
    JsonListStart = ast_cls('JsonListStart', ('src',))
    JsonListEnd = ast_cls('JsonListEnd', ('src',))
    JsonListItem = ast_cls('JsonListItem', ('head', 'val', 'tail'))

    JsonMap = ast_cls('JsonMap', ('head', 'items', 'tail'))
    JsonMapStart = ast_cls('JsonMapStart', ('src',))
    JsonMapEnd = ast_cls('JsonMapEnd', ('src',))
    JsonMapItem = ast_cls(
        'JsonMapItem', ('head', 'key', 'inner', 'val', 'tail'),
    )

    Bool = ast_cls('Bool', ('val', 'src'))
    Null = ast_cls('Null', ('src',))
    String = ast_cls('String', ('val', 'src'))

    Colon = ast_cls('Colon', ('src',))
    Comma = ast_cls('Comma', ('src',))
    Comment = ast_cls('Comment', ('src',))
    Indent = ast_cls('Indent', ('src',))
    NL = ast_cls('NL', ('src',))
    Space = ast_cls('Space', ('src',))

    EOF = ast_cls('EOF', ('src',))


def _or(*args):
    return '({})'.format('|'.join(args))


COLON_RE = re.compile(':')
COMMA_RE = re.compile(',')
COMMENT_RE = re.compile('# .*(\n|$)')
INDENT_RE = re.compile('(?<=\n)(    )+')
NL_RE = re.compile('\n')
SPACE_RE = re.compile('(?<!\n) ')

BOOL_RE = re.compile(_or('TRUE', 'True', 'true', 'FALSE', 'False', 'false'))
NULL_RE = re.compile(_or('NULL', 'null', 'None', 'nil'))
STRING_RE = re.compile(_or(
    r"'[^\n'\\]*(?:\\.[^\n'\\]*)*'", r'"[^\n"\\]*(?:\\.[^\n"\\]*)*"',
))


LIST_START_RE = re.compile(r'\[')
LIST_END_RE = re.compile(']')

LIST_ITEM_RE = re.compile('-   ')

MAP_START_RE = re.compile('{')
MAP_END_RE = re.compile('}')


def _reg_parse(reg, cls, src, offset):
    match = reg.match(src, offset)
    return cls(match.group()), match.end()


def _reg_parse_val(reg, cls, to_val_func, src, offset):
    match = reg.match(src, offset)
    val = to_val_func(match.group())
    return cls(val, match.group()), match.end()


def _to_bool(s):
    return python_ast.literal_eval(s.lower().capitalize())


def _to_s(s):
    # python2 will literal_eval as bytes
    return python_ast.literal_eval('u' + s)


tokenize_processors = (
    (STRING_RE, _reg_parse_val, ast.String, _to_s),
    (BOOL_RE, _reg_parse_val, ast.Bool, _to_bool),
    (NULL_RE, _reg_parse, ast.Null),
    (LIST_START_RE, _reg_parse, ast.JsonListStart),
    (LIST_END_RE, _reg_parse, ast.JsonListEnd),
    (LIST_ITEM_RE, _reg_parse, ast.YamlListItemHead),
    (MAP_START_RE, _reg_parse, ast.JsonMapStart),
    (MAP_END_RE, _reg_parse, ast.JsonMapEnd),
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


def _get_token(tokens, offset, types):
    if not isinstance(tokens[offset], types):
        _token_expected(tokens, offset, types)
    else:
        return tokens[offset], offset + 1


def _parse_rest_of_line_comment_or_nl(tokens, offset):
    ret = []
    while True:
        if isinstance(tokens[offset], ast.Space):
            token, offset = _get_token(tokens, offset, ast.Space)
            ret.append(token)
        elif isinstance(tokens[offset], (ast.Comment, ast.NL)):
            token, offset = _get_token(tokens, offset, (ast.Comment, ast.NL))
            ret.append(token)
            break
        elif isinstance(tokens[offset], ast.EOF):
            break
        else:
            _token_expected(tokens, offset, (ast.Space, ast.Comment, ast.NL))
    return tuple(ret), offset


HEAD_TYPES = (ast.Indent, ast.NL, ast.Comment)


def _parse_head(tokens, offset):
    ret = []
    while True:
        if isinstance(tokens[offset], HEAD_TYPES):
            token, offset = _get_token(tokens, offset, HEAD_TYPES)
            ret.append(token)
        else:
            break
    return tuple(ret), offset


def _parse_indented_list_item_head(tokens, offset):
    head, offset = _parse_head(tokens, offset)
    rest, offset = _get_token(tokens, offset, ast.YamlListItemHead)
    return head + (rest,), offset


def _parse_indented_list(tokens, offset):
    items = []
    while True:
        if not any(
            isinstance(token, ast.YamlListItemHead)
            for token in tokens[offset:]
        ):
            break
        head, offset = _parse_indented_list_item_head(tokens, offset)
        val, offset = _parse_val(tokens, offset)
        tail, offset = _parse_rest_of_line_comment_or_nl(tokens, offset)
        items.append(ast.YamlListItem(head=head, val=val, tail=tail))
    return ast.YamlList(items=tuple(items)), offset


def _parse_json_start(tokens, offset, ast_start):
    ret = []
    part, offset = _get_token(tokens, offset, ast_start)
    ret.append(part)
    multiline = (
        offset < len(tokens) and
        isinstance(tokens[offset], (ast.NL, ast.Comment))
    )
    if multiline:
        tail, offset = _parse_rest_of_line_comment_or_nl(tokens, offset)
        ret.extend(tail)
    return tuple(ret), offset, multiline


def _parse_json_items(tokens, offset, endtoken, parse_item):
    items = []
    while True:
        if isinstance(tokens[offset], endtoken):
            break
        val, offset = parse_item(tokens, offset, head=())
        if offset < len(tokens) and isinstance(tokens[offset], ast.Comma):
            comma, offset = _get_token(tokens, offset, ast.Comma)
            space, offset = _get_token(tokens, offset, ast.Space)
            val = val._replace(tail=val.tail + (comma, space))
        items.append(val)
    return tuple(items), (), offset


def _parse_json_items_multiline(tokens, offset, endtoken, parse_item):
    more_head = ()
    items = []
    while True:
        head, offset = _parse_head(tokens, offset)
        # It's possible that there's comments / newlines after the last
        # item.  In that case, we augment the tail of the previous item.
        # If there are no items, this augments the head of the list itself.
        if isinstance(tokens[offset], endtoken):
            if items:
                items[-1] = items[-1]._replace(tail=items[-1].tail + head)
            else:
                more_head = head
            break
        val, offset = parse_item(tokens, offset, head=head)
        comma, offset = _get_token(tokens, offset, ast.Comma)
        rest, offset = _parse_rest_of_line_comment_or_nl(tokens, offset)
        val = val._replace(tail=val.tail + (comma,) + rest)
        items.append(val)
    return tuple(items), more_head, offset


def _parse_json(tokens, offset, cls, starttoken, endtoken, parse_item):
    head, offset, multiline = _parse_json_start(tokens, offset, starttoken)
    func = _parse_json_items_multiline if multiline else _parse_json_items
    items, more_head, offset = func(tokens, offset, endtoken, parse_item)
    tail, offset = _get_token(tokens, offset, endtoken)
    return cls(head + more_head, items, (tail,)), offset


def _parse_json_list_item(tokens, offset, head):
    val, offset = _parse_val(tokens, offset)
    return ast.JsonListItem(head, val, ()), offset


_parse_json_list = functools.partial(
    _parse_json,
    cls=ast.JsonList, starttoken=ast.JsonListStart, endtoken=ast.JsonListEnd,
    parse_item=_parse_json_list_item,
)


def _parse_json_map_item(tokens, offset, head):
    key, offset = _parse_val(tokens, offset)
    colon, offset = _get_token(tokens, offset, ast.Colon)
    space, offset = _get_token(tokens, offset, ast.Space)
    val, offset = _parse_val(tokens, offset)
    return ast.JsonMapItem(head, key, (colon, space), val, ()), offset


_parse_json_map = functools.partial(
    _parse_json,
    cls=ast.JsonMap, starttoken=ast.JsonMapStart, endtoken=ast.JsonMapEnd,
    parse_item=_parse_json_map_item,
)


VALUE_TOKENS = (ast.String, ast.Bool, ast.Null)
VALUE_START_TOKENS = VALUE_TOKENS + (ast.JsonListStart, ast.JsonMapStart)


def _parse_val(tokens, offset):
    if isinstance(tokens[offset], VALUE_TOKENS):
        return _get_token(tokens, offset, VALUE_TOKENS)
    elif isinstance(tokens[offset], ast.JsonListStart):
        return _parse_json_list(tokens, offset)
    elif isinstance(tokens[offset], ast.JsonMapStart):
        return _parse_json_map(tokens, offset)
    else:
        _token_expected(tokens, offset, VALUE_START_TOKENS)


def _parse_body(tokens, offset):
    if isinstance(tokens[offset], ast.YamlListItemHead):
        return _parse_indented_list(tokens, offset)
    else:
        return _parse_val(tokens, offset)


def _parse_tail(tokens, offset):
    # The file may end in newlines whitespace and comments
    ret = []
    while True:
        if isinstance(tokens[offset], ast.EOF):
            break
        token, offset = _get_token(
            tokens, offset, (ast.NL, ast.Space, ast.Comment),
        )
        ret.append(token)
    return tuple(ret), offset


def parse(src):
    tokens, offset = tokenize(src), 0

    head, offset = _parse_head(tokens, offset)
    body, offset = _parse_body(tokens, offset)
    tail, offset = _parse_tail(tokens, offset)

    return ast.Doc(head, body, tail)


def unparse(ast_obj):
    src = ''
    for field in ast_obj._fields:
        attr = getattr(ast_obj, field)
        if field == 'src':
            src += attr
        elif type(attr) is tuple:
            for el in attr:
                src += unparse(el)
        elif isinstance(attr, tuple):
            src += unparse(attr)
    return src


def debug(ast_obj, _indent=0):
    if 'src' in ast_obj._fields:
        return repr(ast_obj)
    else:
        class state:
            indent = _indent

        @contextlib.contextmanager
        def indented():
            state.indent += 1
            yield
            state.indent -= 1

        def indentstr():
            return state.indent * '    '

        out = type(ast_obj).__name__ + '(\n'
        with indented():
            for field in ast_obj._fields:
                attr = getattr(ast_obj, field)
                if attr == ():
                    representation = repr(attr)
                elif type(attr) is tuple:
                    representation = '(\n'
                    with indented():
                        for el in attr:
                            representation += '{}{},\n'.format(
                                indentstr(), debug(el, state.indent),
                            )
                    representation += indentstr() + ')'
                elif isinstance(attr, tuple):
                    representation = debug(attr, state.indent)
                else:
                    raise AssertionError('unreachable!')
                out += '{}{}={},\n'.format(indentstr(), field, representation)
        out += indentstr() + ')'
        return out
