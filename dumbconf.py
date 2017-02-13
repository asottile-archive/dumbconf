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


def _pattern_expected(tokens, offset, pattern):
    expected = _pattern_expected_tokens(pattern)
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
    Doc = ast_cls('Doc', ('head', 'val', 'tail'))

    List = ast_cls('List', ('head', 'items', 'tail'))
    ListStart = ast_cls('ListStart', ('src',))
    ListEnd = ast_cls('ListEnd', ('src',))
    ListItem = ast_cls('ListItem', ('head', 'val', 'tail'))

    Map = ast_cls('Map', ('head', 'items', 'tail'))
    MapStart = ast_cls('MapStart', ('src',))
    MapEnd = ast_cls('MapEnd', ('src',))
    MapItem = ast_cls('MapItem', ('head', 'key', 'inner', 'val', 'tail'))

    Bool = ast_cls('Bool', ('val', 'src'))
    Null = ast_cls('Null', ('val', 'src',))
    String = ast_cls('String', ('val', 'src'))
    BareWordKey = ast_cls('BareWordKey', ('val', 'src'))

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
BARE_WORD_KEY_RE = re.compile('[A-Za-z_][a-zA-Z0-9_-]*')


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


def _to_s(s):
    # python2 will literal_eval as bytes
    return python_ast.literal_eval('u' + s)


def _to_bool(s):
    return python_ast.literal_eval(s.lower().capitalize())


def _to_null(s):
    return None


def _identity(s):
    return s


tokenize_processors = (
    (STRING_RE, _reg_parse_val, ast.String, _to_s),
    (BOOL_RE, _reg_parse_val, ast.Bool, _to_bool),
    (NULL_RE, _reg_parse_val, ast.Null, _to_null),
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
    # Lowest priority token
    (BARE_WORD_KEY_RE, _reg_parse_val, ast.BareWordKey, _identity),
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


def _matches_pattern(
    tokens, offset, pattern,
    cb=lambda tokens, offset, pattern: None,
):
    """Basically a regex language for tokens

    `cb` is called on failure and should raise or return `None`
    """
    start = offset

    if isinstance(pattern, Pattern):
        for seq in pattern.sequence:
            ret = _matches_pattern(tokens, offset, seq)
            if ret is None:
                return cb(tokens, offset, seq)
            else:
                _, offset, _ = ret
        return Match(start, offset, tokens)
    elif isinstance(pattern, Or):
        for choice in pattern.choices:
            ret = _matches_pattern(tokens, offset, choice)
            if ret is not None:
                return ret
        else:
            return cb(tokens, offset, pattern)
    elif isinstance(pattern, Star):
        while True:
            ret = _matches_pattern(tokens, offset, pattern.pattern)
            if ret is None:
                break
            else:
                _, offset, _ = ret
        return Match(start, offset, tokens)
    elif isinstance(tokens[offset], pattern):
        return Match(start, offset + 1, tokens)
    else:
        return cb(tokens, offset, pattern)


def _get_pattern(tokens, offset, pattern, single=False):
    match = _matches_pattern(tokens, offset, pattern, _pattern_expected)
    val, offset = match.match()
    if single:
        val, = val
    return val, offset


PT_REST_OF_LINE = Or(ast.NL, Pattern(Star(ast.Space), ast.Comment))
PT_HEAD = Star(Or(ast.Indent, ast.NL, ast.Comment))
PT_COLON_SPACE = Pattern(ast.Colon, ast.Space)
PT_COMMA_SPACE = Pattern(ast.Comma, ast.Space)
PT_VALUE_TOKENS = Or(ast.String, ast.Bool, ast.Null)
PT_KEY = Or(PT_VALUE_TOKENS, ast.BareWordKey)


def _parse_json_start(tokens, offset, ast_start):
    ret, offset = _get_pattern(tokens, offset, ast_start)
    match = _matches_pattern(tokens, offset, PT_REST_OF_LINE)
    if match:
        rest, offset = match.match()
        ret += rest
    return ret, offset, bool(match)


def _parse_json_items(tokens, offset, endtoken, parse_item):
    items = []
    while True:
        if isinstance(tokens[offset], endtoken):
            break
        val, offset = parse_item(tokens, offset, head=())
        if offset < len(tokens) and isinstance(tokens[offset], ast.Comma):
            comma_space, offset = _get_pattern(tokens, offset, PT_COMMA_SPACE)
            val = val._replace(tail=val.tail + comma_space)
        items.append(val)
    return tuple(items), (), offset


def _parse_json_items_multiline(tokens, offset, endtoken, parse_item):
    more_head = ()
    items = []
    while True:
        head, offset = _get_pattern(tokens, offset, PT_HEAD)
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
        comma, offset = _get_pattern(tokens, offset, ast.Comma)
        rest, offset = _get_pattern(tokens, offset, PT_REST_OF_LINE)
        val = val._replace(tail=val.tail + comma + rest)
        items.append(val)
    return tuple(items), more_head, offset


def _parse_json(tokens, offset, cls, starttoken, endtoken, parse_item):
    head, offset, multiline = _parse_json_start(tokens, offset, starttoken)
    func = _parse_json_items_multiline if multiline else _parse_json_items
    items, more_head, offset = func(tokens, offset, endtoken, parse_item)
    tail, offset = _get_pattern(tokens, offset, endtoken)
    return cls(head + more_head, items, tail), offset


def _parse_json_list_item(tokens, offset, head):
    val, offset = _parse_val(tokens, offset)
    return ast.ListItem(head, val, ()), offset


_parse_json_list = functools.partial(
    _parse_json,
    cls=ast.List, starttoken=ast.ListStart, endtoken=ast.ListEnd,
    parse_item=_parse_json_list_item,
)


def _parse_json_map_item(tokens, offset, head):
    key, offset = _get_pattern(tokens, offset, PT_KEY, single=True)
    colon_space, offset = _get_pattern(tokens, offset, PT_COLON_SPACE)
    val, offset = _parse_val(tokens, offset)
    return ast.MapItem(head, key, colon_space, val, ()), offset


_parse_json_map = functools.partial(
    _parse_json,
    cls=ast.Map, starttoken=ast.MapStart, endtoken=ast.MapEnd,
    parse_item=_parse_json_map_item,
)


def _parse_val(tokens, offset):
    if _matches_pattern(tokens, offset, PT_VALUE_TOKENS):
        return _get_pattern(tokens, offset, PT_VALUE_TOKENS, single=True)
    elif _matches_pattern(tokens, offset, ast.ListStart):
        return _parse_json_list(tokens, offset)
    elif _matches_pattern(tokens, offset, ast.MapStart):
        return _parse_json_map(tokens, offset)
    else:
        missing_pattern = Or(PT_VALUE_TOKENS, ast.ListStart, ast.MapStart)
        _pattern_expected(tokens, offset, missing_pattern)


def _parse_eof(tokens, offset):
    """Parse the end of the file"""
    ret, offset = _get_pattern(tokens, offset, Star(PT_REST_OF_LINE))
    _get_pattern(tokens, offset, ast.EOF)
    return ret, offset


def parse(src):
    tokens, offset = tokenize(src), 0

    head, offset = _get_pattern(tokens, offset, PT_HEAD)
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


def _to_python_value(ast_obj):
    if isinstance(ast_obj, ast.Doc):
        return _to_python_value(ast_obj.val)
    elif isinstance(
            ast_obj, (ast.BareWordKey, ast.Bool, ast.Null, ast.String),
    ):
        return ast_obj.val
    elif isinstance(ast_obj, ast.List):
        return [_to_python_value(item.val) for item in ast_obj.items]
    elif isinstance(ast_obj, ast.Map):
        return collections.OrderedDict(
            (_to_python_value(item.key), _to_python_value(item.val))
            for item in ast_obj.items
        )
    else:
        raise AssertionError('Unknown ast: {!r}'.format(ast_obj))


def loads(s):
    """Return a python object"""
    return _to_python_value(parse(s))
