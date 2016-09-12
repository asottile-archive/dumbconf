# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

import dumbconf
from dumbconf import ast
from dumbconf import ParseError


def parse(s):
    """An assertion that roundtripping works"""
    ret = dumbconf.parse(s)
    assert dumbconf.unparse(ret) == s
    return ret


def test_parse_error_no_source():
    assert str(ParseError('', 0, 'No source!')) == 'No source!'


def test_parse_error_trivial():
    assert str(ParseError('src', 0)) == (
        '\n\n'
        'Line 1, column 1\n\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '1   |src\n'
        '     ^\n'
    )


def test_parse_error_with_message():
    assert str(ParseError('src', 0, 'Error!')) == (
        'Error!\n\n'
        'Line 1, column 1\n\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '1   |src\n'
        '     ^\n'
    )


def test_parse_error_end_of_line():
    assert str(ParseError('foo\nbar\n', 3, 'Error!')) == (
        'Error!\n\n'
        'Line 1, column 4\n\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '1   |foo\n'
        '        ^\n'
        '2   |bar\n'
    )


def test_parse_error_multiple_lines():
    assert str(ParseError('foo\nbar\n', 4)) == (
        '\n\n'
        'Line 2, column 1\n'
        '\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '1   |foo\n'
        '2   |bar\n'
        '     ^\n'
    )


def test_parse_error_many_lines():
    assert str(ParseError('a\nb\nc\nd\ne\nf\ng\n', 6)) == (
        '\n\n'
        'Line 4, column 1\n'
        '\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '2   |b\n'
        '3   |c\n'
        '4   |d\n'
        '     ^\n'
        '5   |e\n'
        '6   |f\n'
    )


def test_debug():
    ret = dumbconf.debug(dumbconf.parse('[True]'))
    assert ret == (
        'Doc(\n'
        '    head=(),\n'
        '    body=JsonList(\n'
        '        head=(\n'
        "            JsonListStart(src='['),\n"
        '        ),\n'
        '        items=(\n'
        '            JsonListItem(\n'
        '                head=(),\n'
        "                val=Bool(val=True, src='True'),\n"
        '                tail=(),\n'
        '            ),\n'
        '        ),\n'
        '        tail=(\n'
        "            JsonListEnd(src=']'),\n"
        '        ),\n'
        '    ),\n'
        '    tail=(),\n'
        ')'
    )


@pytest.mark.parametrize(
    ('s', 'expected_val'),
    (
        ('TRUE', True), ('True', True), ('true', True),
        ('FALSE', False), ('False', False), ('false', False),
    ),
)
def test_parse_boolean(s, expected_val):
    expected = ast.Doc(
        head=(), body=ast.Bool(val=expected_val, src=s), tail=(),
    )
    assert parse(s) == expected


@pytest.mark.parametrize('s', ('NULL', 'null', 'None', 'nil'))
def test_parse_null(s):
    expected = ast.Doc(head=(), body=ast.Null(src=s), tail=())
    assert parse(s) == expected


@pytest.mark.parametrize('quote', ("'", '"'))
@pytest.mark.parametrize(
    ('s', 'expected_val'),
    (
        ("'foo'", 'foo'),
        (r"'foo\'bar'", "foo'bar"),
        ("'\\u2603'", "☃"),
    ),
)
def test_parse_quoted_string(quote, s, expected_val):
    s = s.replace("'", quote)
    expected_val = expected_val.replace("'", quote)
    expected = ast.Doc(
        head=(), body=ast.String(val=expected_val, src=s), tail=(),
    )
    assert parse(s) == expected


def test_parse_indented_list():
    ret = parse(
        '-   True\n'
        '-   False\n'
    )
    expected = ast.Doc(
        head=(),
        body=ast.YamlList(items=(
            ast.YamlListItem(
                head=(ast.YamlListItemHead('-   '),),
                val=ast.Bool(True, 'True'),
                tail=(ast.NL('\n'),),
            ),
            ast.YamlListItem(
                head=(ast.YamlListItemHead('-   '),),
                val=ast.Bool(False, 'False'),
                tail=(ast.NL('\n'),),
            ),
        )),
        tail=(),
    )
    assert ret == expected


def test_parse_indented_list_with_inline_comment():
    ret = parse('-   "hi"  # hello\n')
    expected = ast.Doc(
        head=(),
        body=ast.YamlList(items=(
            ast.YamlListItem(
                head=(ast.YamlListItemHead('-   '),),
                val=ast.String('hi', '"hi"'),
                tail=(
                    ast.Space(' '), ast.Space(' '), ast.Comment('# hello\n'),
                ),
            ),
        )),
        tail=(),
    )
    assert ret == expected


def test_parse_indented_list_no_nl_at_eof():
    ret = parse('-   "hi"')
    expected = ast.Doc(
        head=(),
        body=ast.YamlList(items=(
            ast.YamlListItem(
                head=(ast.YamlListItemHead('-   '),),
                val=ast.String('hi', '"hi"'),
                tail=(),
            ),
        )),
        tail=(),
    )
    assert ret == expected


def test_parse_indented_list_internal_comments():
    ret = parse(
        '-   "hi"\n'
        '\n'
        '# but actually\n'
        '-   "ohai"\n'
    )
    expected = ast.Doc(
        head=(),
        body=ast.YamlList(items=(
            ast.YamlListItem(
                head=(ast.YamlListItemHead('-   '),),
                val=ast.String('hi', '"hi"'),
                tail=(ast.NL('\n'),),
            ),
            ast.YamlListItem(
                head=(
                    ast.NL('\n'),
                    ast.Comment('# but actually\n'),
                    ast.YamlListItemHead('-   '),
                ),
                val=ast.String('ohai', '"ohai"'),
                tail=(ast.NL('\n'),),
            ),
        )),
        tail=(),
    )
    assert ret == expected


def test_json_trivial_list():
    ret = parse('[]')
    expected = ast.Doc(
        head=(),
        body=ast.JsonList(
            head=(ast.JsonListStart('['),),
            items=(),
            tail=(ast.JsonListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_one_value_inline():
    ret = parse('[True]')
    expected = ast.Doc(
        head=(),
        body=ast.JsonList(
            head=(ast.JsonListStart('['),),
            items=(
                ast.JsonListItem(
                    head=(), val=ast.Bool(val=True, src='True'), tail=(),
                ),
            ),
            tail=(ast.JsonListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_several_values_inline():
    ret = parse('[True, False]')
    expected = ast.Doc(
        head=(),
        body=ast.JsonList(
            head=(ast.JsonListStart('['),),
            items=(
                ast.JsonListItem(
                    head=(),
                    val=ast.Bool(val=True, src='True'),
                    tail=(ast.Comma(','), ast.Space(' ')),
                ),
                ast.JsonListItem(
                    head=(),
                    val=ast.Bool(val=False, src='False'),
                    tail=(),
                ),
            ),
            tail=(ast.JsonListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_multiline_trivial():
    ret = parse('[\n]')
    expected = ast.Doc(
        head=(),
        body=ast.JsonList(
            head=(ast.JsonListStart('['), ast.NL('\n')),
            items=(),
            tail=(ast.JsonListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_multiline_comments():
    ret = parse(
        '[\n'
        '    # Comment\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        body=ast.JsonList(
            head=(
                ast.JsonListStart('['), ast.NL('\n'),
                ast.Indent('    '), ast.Comment('# Comment\n'),
            ),
            items=(),
            tail=(ast.JsonListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_multiline():
    ret = parse(
        '[\n'
        '    True,\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        body=ast.JsonList(
            head=(ast.JsonListStart('['), ast.NL('\n')),
            items=(
                ast.JsonListItem(
                    head=(ast.Indent('    '),),
                    val=ast.Bool(val=True, src='True'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.JsonListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_multiline_comment_before():
    ret = parse(
        '[\n'
        '    # Hello\n'
        '    True,\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        body=ast.JsonList(
            head=(ast.JsonListStart('['), ast.NL('\n')),
            items=(
                ast.JsonListItem(
                    head=(
                        ast.Indent('    '), ast.Comment('# Hello\n'),
                        ast.Indent('    '),
                    ),
                    val=ast.Bool(val=True, src='True'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.JsonListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_multiline_comment_after():
    ret = parse(
        '[\n'
        '    True,\n'
        '    # Comment\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        body=ast.JsonList(
            head=(ast.JsonListStart('['), ast.NL('\n')),
            items=(
                ast.JsonListItem(
                    head=(ast.NL('    '),),
                    val=ast.Bool(val=True, src='True'),
                    tail=(
                        ast.Comma(','), ast.NL('\n'),
                        ast.Indent('    '), ast.Comment('# Comment\n'),
                    ),
                ),
            ),
            tail=(ast.JsonListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_file_starting_in_ws():
    ret = parse('\n\nTrue')
    expected = ast.Doc(
        head=(ast.NL('\n'), ast.NL('\n')),
        body=ast.Bool(val=True, src='True'),
        tail=(),
    )
    assert ret == expected


def test_file_ending_in_ws():
    ret = parse('True\n')
    expected = ast.Doc(
        head=(), body=ast.Bool(val=True, src='True'), tail=(ast.NL('\n'),),
    )
    assert ret == expected


def test_file_starting_with_comments():
    ret = parse('# hello\nTrue')
    expected = ast.Doc(
        head=(ast.Comment('# hello\n'),),
        body=ast.Bool(val=True, src='True'),
        tail=(),
    )
    assert ret == expected


def test_file_ending_in_comment():
    ret = parse('True # ohai\n')
    expected = ast.Doc(
        head=(),
        body=ast.Bool(val=True, src='True'),
        tail=(ast.Space(' '), ast.Comment('# ohai\n')),
    )
    assert ret == expected


def test_file_ending_in_comment_no_nl():
    ret = parse('True # ohai')
    expected = ast.Doc(
        head=(),
        body=ast.Bool(val=True, src='True'),
        tail=(ast.Space(' '), ast.Comment('# ohai')),
    )
    assert ret == expected


def test_file_ending_in_several_comments():
    ret = parse('True\n# hello\n# there\n')
    expected = ast.Doc(
        head=(),
        body=ast.Bool(val=True, src='True'),
        tail=(
            ast.NL('\n'), ast.Comment('# hello\n'), ast.Comment('# there\n'),
        ),
    )
    assert ret == expected
