from __future__ import absolute_import
from __future__ import unicode_literals

import ast as python_ast
import collections
import re


class ParseError(ValueError):
    def __init__(self, src, offset, msg=None):
        self.src = src
        self.offset = offset
        self.msg = msg

    def __str__(self):
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


def ast_cls(*args, **kwargs):
    # TODO: add more useful things here
    return collections.namedtuple(*args, **kwargs)


class ast:
    Doc = ast_cls('Doc', ('head', 'body', 'tail'))

    YamlList = ast_cls('YamlList', ('items',))
    YamlListItem = ast_cls('YamlListItem', ('head', 'val', 'tail'))
    YamlListItemHead = ast_cls('YamlListItemHead', ('src',))

    Bool = ast_cls('Bool', ('val', 'src'))
    Null = ast_cls('Null', ('src',))
    String = ast_cls('String', ('val', 'src'))

    Comment = ast_cls('Comment', ('src',))
    WS = ast_cls('WS', ('src',))


def _or(*args):
    return '({})'.format('|'.join(args))


def _reg_or(*args):
    return _or(*(reg.pattern for reg in args))


COMMENT_RE = re.compile('# .*(\n|$)')
NL_RE = re.compile('\n')
SPACES_RE = re.compile(' +')
WS_RE = re.compile(r'\s+')

BOOL_RE = re.compile(_or('TRUE', 'True', 'true', 'FALSE', 'False', 'false'))
NULL_RE = re.compile(_or('NULL', 'null', 'None', 'nil'))
STRING_RE = re.compile(_or(
    r"'[^\n'\\]*(?:\\.[^\n'\\]*)*'", r'"[^\n"\\]*(?:\\.[^\n"\\]*)*"',
))
LIST_ITEM_RE = re.compile('-   ')

LIST_CONTINUES_RE = re.compile(
    _reg_or(COMMENT_RE, NL_RE) + '*' + LIST_ITEM_RE.pattern,
)


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


def _parse_rest_of_line_comment_or_nl(src, offset):
    ret = []
    srclen = len(src)
    while offset < srclen:
        if SPACES_RE.match(src, offset):
            part, offset = _reg_parse(SPACES_RE, ast.WS, src, offset)
            ret.append(part)
        elif NL_RE.match(src, offset):
            part, offset = _reg_parse(NL_RE, ast.WS, src, offset)
            ret.append(part)
            break
        elif COMMENT_RE.match(src, offset):
            part, offset = _reg_parse(COMMENT_RE, ast.WS, src, offset)
            ret.append(part)
            break
        else:
            raise ParseError(src, offset, 'Expected comment or end of line')
    return tuple(ret), offset


def _parse_indented_list_item_head(src, offset):
    head, offset = _parse_head(src, offset)
    rest, offset = _reg_parse(LIST_ITEM_RE, ast.YamlListItemHead, src, offset)
    return head + (rest,), offset


def _parse_indented_list(src, offset):
    items = []
    srclen = len(src)
    while offset < srclen:
        if not LIST_CONTINUES_RE.match(src, offset):
            break
        head, offset = _parse_indented_list_item_head(src, offset)
        val, offset = _parse_val(src, offset)
        tail, offset = _parse_rest_of_line_comment_or_nl(src, offset)
        items.append(ast.YamlListItem(head=head, val=val, tail=tail))
    return ast.YamlList(items=tuple(items)), offset


def _parse_head(src, offset):
    ret = []
    while True:
        if NL_RE.match(src, offset):
            part, offset = _reg_parse(NL_RE, ast.WS, src, offset)
        elif COMMENT_RE.match(src, offset):
            part, offset = _reg_parse(COMMENT_RE, ast.WS, src, offset)
        else:
            break
        ret.append(part)
    return tuple(ret), offset


def _parse_val(src, offset):
    if src[offset] in ('"', "'"):
        return _reg_parse_val(STRING_RE, ast.String, _to_s, src, offset)
    elif BOOL_RE.match(src, offset):
        return _reg_parse_val(BOOL_RE, ast.Bool, _to_bool, src, offset)
    elif NULL_RE.match(src, offset):
        return _reg_parse(NULL_RE, ast.Null, src, offset)
    else:
        raise ParseError(src, offset, msg='Unknown top level contruct')


def _parse_body(src, offset):
    if src[offset] == '-':
        return _parse_indented_list(src, offset)
    else:
        return _parse_val(src, offset)


def _parse_tail(src, offset):
    # The file may end in newlines whitespace and comments
    ret = []
    srclen = len(src)
    while offset < srclen:
        if WS_RE.match(src, offset):
            part, offset = _reg_parse(WS_RE, ast.WS, src, offset)
        elif COMMENT_RE.match(src, offset):
            part, offset = _reg_parse(COMMENT_RE, ast.Comment, src, offset)
        else:
            raise ParseError(src, offset)
        ret.append(part)
    return tuple(ret), offset


def parse(src):
    offset = 0

    head, offset = _parse_head(src, offset)
    body, offset = _parse_body(src, offset)
    tail, offset = _parse_tail(src, offset)

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
