from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib
import functools

from dumbconf import ast
from dumbconf._tokenize import tokenize
from dumbconf._tre import get_pattern
from dumbconf._tre import matches_pattern
from dumbconf._tre import Or
from dumbconf._tre import Pattern
from dumbconf._tre import pattern_expected
from dumbconf._tre import Star


PT_REST_OF_LINE = Or(ast.NL, Pattern(Star(ast.Space), ast.Comment))
PT_HEAD = Star(Or(ast.Indent, ast.NL, ast.Comment))
PT_COLON_SPACE = Pattern(ast.Colon, ast.Space)
PT_COMMA_SPACE = Pattern(ast.Comma, ast.Space)
PT_VALUE_TOKENS = Or(ast.Bool, ast.Null, ast.Float, ast.Int, ast.String)
PT_KEY = Or(PT_VALUE_TOKENS, ast.BareWordKey)


def _parse_start(tokens, offset, ast_start):
    ret, offset = get_pattern(tokens, offset, ast_start)
    match = matches_pattern(tokens, offset, PT_REST_OF_LINE)
    if match:
        rest, offset = match.match()
        ret += rest
    return ret, offset, bool(match)


def _parse_items(tokens, offset, endtoken, parse_item):
    items = []
    while not matches_pattern(tokens, offset, endtoken):
        val, offset = parse_item(tokens, offset, head=())
        if not matches_pattern(tokens, offset, endtoken):
            comma_space, offset = get_pattern(tokens, offset, PT_COMMA_SPACE)
            val = val._replace(tail=val.tail + comma_space)
        items.append(val)
    return tuple(items), (), offset


def _parse_items_multiline(tokens, offset, endtoken, parse_item):
    more_head = ()
    items = []
    while True:
        head, offset = get_pattern(tokens, offset, PT_HEAD)
        # It's possible that there's comments / newlines after the last
        # item.  In that case, we augment the tail of the previous item.
        # If there are no items, this augments the head of the list itself.
        if matches_pattern(tokens, offset, endtoken):
            if items:
                items[-1] = items[-1]._replace(tail=items[-1].tail + head)
            else:
                more_head = head
            break
        val, offset = parse_item(tokens, offset, head=head)
        comma, offset = get_pattern(tokens, offset, ast.Comma)
        # Allow multiple items to be on a single line
        if matches_pattern(tokens, offset, PT_REST_OF_LINE):
            rest, offset = get_pattern(tokens, offset, PT_REST_OF_LINE)
        else:
            rest, offset = get_pattern(tokens, offset, ast.Space)
        val = val._replace(tail=val.tail + comma + rest)
        items.append(val)
    return tuple(items), more_head, offset


def _parse_container(tokens, offset, cls, starttoken, endtoken, parse_item):
    head, offset, multiline = _parse_start(tokens, offset, starttoken)
    func = _parse_items_multiline if multiline else _parse_items
    items, more_head, offset = func(tokens, offset, endtoken, parse_item)
    tail, offset = get_pattern(tokens, offset, endtoken)
    return cls(head + more_head, items, tail), offset


def _parse_list_item(tokens, offset, head):
    val, offset = _parse_val(tokens, offset)
    return ast.ListItem(head, val, ()), offset


_parse_list = functools.partial(
    _parse_container,
    cls=ast.List, starttoken=ast.ListStart, endtoken=ast.ListEnd,
    parse_item=_parse_list_item,
)


def _parse_map_item(tokens, offset, head):
    key, offset = get_pattern(tokens, offset, PT_KEY, single=True)
    colon_space, offset = get_pattern(tokens, offset, PT_COLON_SPACE)
    val, offset = _parse_val(tokens, offset)
    return ast.MapItem(head, key, colon_space, val, ()), offset


_parse_map = functools.partial(
    _parse_container,
    cls=ast.Map, starttoken=ast.MapStart, endtoken=ast.MapEnd,
    parse_item=_parse_map_item,
)


def _parse_val(tokens, offset):
    if matches_pattern(tokens, offset, PT_VALUE_TOKENS):
        return get_pattern(tokens, offset, PT_VALUE_TOKENS, single=True)
    elif matches_pattern(tokens, offset, ast.ListStart):
        return _parse_list(tokens, offset)
    elif matches_pattern(tokens, offset, ast.MapStart):
        return _parse_map(tokens, offset)
    else:
        missing_pattern = Or(PT_VALUE_TOKENS, ast.ListStart, ast.MapStart)
        pattern_expected(tokens, offset, missing_pattern)


def _parse_eof(tokens, offset):
    """Parse the end of the file"""
    ret, offset = get_pattern(tokens, offset, Star(PT_REST_OF_LINE))
    get_pattern(tokens, offset, ast.EOF)
    return ret, offset


def parse(src):
    tokens, offset = tokenize(src), 0

    head, offset = get_pattern(tokens, offset, PT_HEAD)
    val, offset = _parse_val(tokens, offset)
    tail, offset = _parse_eof(tokens, offset)

    return ast.Doc(head, val, tail)


def unparse(ast_obj):
    src = ''
    for field in ast_obj._fields:
        attr = getattr(ast_obj, field)
        if field == 'src':
            src += attr
        elif type(attr) is tuple:
            for el in attr:
                src += unparse(el)
        elif isinstance(attr, ast.AST):
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
                elif isinstance(attr, ast.AST):
                    representation = debug(attr, state.indent)
                else:
                    raise AssertionError('unreachable!')
                out += '{}{}={},\n'.format(indentstr(), field, representation)
        out += indentstr() + ')'
        return out
