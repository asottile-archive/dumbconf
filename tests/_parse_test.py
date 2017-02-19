# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from dumbconf import ast
from dumbconf._error import ParseError
from dumbconf._parse import debug
from dumbconf._parse import parse as parse_actual
from dumbconf._parse import unparse


def parse(s):
    """An assertion that roundtripping works"""
    ret = parse_actual(s)
    assert unparse(ret) == s
    return ret


def _assert_parse_error(src, s):
    with pytest.raises(ParseError) as excinfo:
        parse(src)
    assert str(excinfo.value) == s


def test_debug():
    ret = debug(parse('[True]'))
    assert ret == (
        'Doc(\n'
        '    head=(),\n'
        '    val=List(\n'
        '        head=(\n'
        "            ListStart(src='['),\n"
        '        ),\n'
        '        items=(\n'
        '            ListItem(\n'
        '                head=(),\n'
        "                val=Bool(val=True, src='True'),\n"
        '                tail=(),\n'
        '            ),\n'
        '        ),\n'
        '        tail=(\n'
        "            ListEnd(src=']'),\n"
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
        head=(), val=ast.Bool(val=expected_val, src=s), tail=(),
    )
    assert parse(s) == expected


@pytest.mark.parametrize('s', ('NULL', 'null', 'None', 'nil'))
def test_parse_null(s):
    expected = ast.Doc(head=(), val=ast.Null(None, src=s), tail=())
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
        head=(), val=ast.String(val=expected_val, src=s), tail=(),
    )
    assert parse(s) == expected


def test_json_trivial_list():
    ret = parse('[]')
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['),),
            items=(),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_one_value_inline():
    ret = parse('[True]')
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['),),
            items=(
                ast.ListItem(
                    head=(), val=ast.Bool(val=True, src='True'), tail=(),
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_several_values_inline():
    ret = parse('[True, False]')
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['),),
            items=(
                ast.ListItem(
                    head=(),
                    val=ast.Bool(val=True, src='True'),
                    tail=(ast.Comma(','), ast.Space(' ')),
                ),
                ast.ListItem(
                    head=(),
                    val=ast.Bool(val=False, src='False'),
                    tail=(),
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_regression_inline_list_missing_comma():
    _assert_parse_error(
        '[TrueFalse]',
        'Expected one of (Comma) but received Bool\n\n'
        'Line 1, column 6\n\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '1   |[TrueFalse]\n'
        '          ^\n',
    )


def test_json_list_multiline_trivial():
    ret = parse('[\n]')
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(),
            tail=(ast.ListEnd(']'),),
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
        val=ast.List(
            head=(
                ast.ListStart('['), ast.NL('\n'),
                ast.Indent('    '), ast.Comment('# Comment\n'),
            ),
            items=(),
            tail=(ast.ListEnd(']'),),
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
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(
                ast.ListItem(
                    head=(ast.Indent('    '),),
                    val=ast.Bool(val=True, src='True'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.ListEnd(']'),),
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
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(
                ast.ListItem(
                    head=(
                        ast.Indent('    '), ast.Comment('# Hello\n'),
                        ast.Indent('    '),
                    ),
                    val=ast.Bool(val=True, src='True'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.ListEnd(']'),),
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
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(
                ast.ListItem(
                    head=(ast.NL('    '),),
                    val=ast.Bool(val=True, src='True'),
                    tail=(
                        ast.Comma(','), ast.NL('\n'),
                        ast.Indent('    '), ast.Comment('# Comment\n'),
                    ),
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_list_multiple_items_multiline():
    ret = parse(
        '[\n'
        '    True,\n'
        '    False,\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(
                ast.ListItem(
                    head=(ast.NL('    '),),
                    val=ast.Bool(val=True, src='True'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
                ast.ListItem(
                    head=(ast.NL('    '),),
                    val=ast.Bool(val=False, src='False'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_map_trivial():
    ret = parse('{}')
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(ast.MapStart('{'),),
            items=(),
            tail=(ast.MapEnd('}'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_map_one_element_inline():
    ret = parse('{True: False}')
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(ast.MapStart('{'),),
            items=(
                ast.MapItem(
                    head=(),
                    key=ast.Bool(val=True, src='True'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=False, src='False'),
                    tail=(),
                ),
            ),
            tail=(ast.MapEnd('}'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_map_multiple_elements_inline():
    ret = parse('{True: False, False: True}')
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(ast.MapStart('{'),),
            items=(
                ast.MapItem(
                    head=(),
                    key=ast.Bool(val=True, src='True'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=False, src='False'),
                    tail=(ast.Comma(','), ast.Space(' ')),
                ),
                ast.MapItem(
                    head=(),
                    key=ast.Bool(val=False, src='False'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=True, src='True'),
                    tail=(),
                ),
            ),
            tail=(ast.MapEnd('}'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_map_multiline_trivial():
    ret = parse('{\n}')
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(ast.MapStart('{'), ast.NL('\n')),
            items=(),
            tail=(ast.MapEnd('}'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_json_map_multiline_one_element():
    ret = parse(
        '{\n'
        '    True: False,\n'
        '}'
    )
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(ast.MapStart('{'), ast.NL('\n')),
            items=(
                ast.MapItem(
                    head=(ast.Indent('    '),),
                    key=ast.Bool(val=True, src='True'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=False, src='False'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.MapEnd('}'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_comment_at_start_of_multiline_json():
    ret = parse(
        '{  # bar\n'
        '    True: False,\n'
        '}'
    )
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(
                ast.MapStart('{'), ast.Space(' '), ast.Space(' '),
                ast.Comment('# bar\n'),
            ),
            items=(
                ast.MapItem(
                    head=(ast.Indent('    '),),
                    key=ast.Bool(val=True, src='True'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=False, src='False'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.MapEnd('}'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_map_bare_word_key():
    ret = parse("{_Key-str1ng: 'value'}")
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(ast.MapStart('{'),),
            items=(
                ast.MapItem(
                    head=(),
                    key=ast.BareWordKey('_Key-str1ng', '_Key-str1ng'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.String(val='value', src="'value'"),
                    tail=(),
                ),
            ),
            tail=(ast.MapEnd('}'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_file_starting_in_ws():
    ret = parse('\n\nTrue')
    expected = ast.Doc(
        head=(ast.NL('\n'), ast.NL('\n')),
        val=ast.Bool(val=True, src='True'),
        tail=(),
    )
    assert ret == expected


def test_file_ending_in_ws():
    ret = parse('True\n')
    expected = ast.Doc(
        head=(), val=ast.Bool(val=True, src='True'), tail=(ast.NL('\n'),),
    )
    assert ret == expected


def test_file_starting_with_comments():
    ret = parse('# hello\nTrue')
    expected = ast.Doc(
        head=(ast.Comment('# hello\n'),),
        val=ast.Bool(val=True, src='True'),
        tail=(),
    )
    assert ret == expected


def test_file_ending_in_comment():
    ret = parse('True # ohai\n')
    expected = ast.Doc(
        head=(),
        val=ast.Bool(val=True, src='True'),
        tail=(ast.Space(' '), ast.Comment('# ohai\n')),
    )
    assert ret == expected


def test_file_ending_in_comment_no_nl():
    ret = parse('True # ohai')
    expected = ast.Doc(
        head=(),
        val=ast.Bool(val=True, src='True'),
        tail=(ast.Space(' '), ast.Comment('# ohai')),
    )
    assert ret == expected


def test_file_ending_in_several_comments():
    ret = parse('True\n# hello\n# there\n')
    expected = ast.Doc(
        head=(),
        val=ast.Bool(val=True, src='True'),
        tail=(
            ast.NL('\n'), ast.Comment('# hello\n'), ast.Comment('# there\n'),
        ),
    )
    assert ret == expected


def test_parse_error_no_contents():
    _assert_parse_error(
        '',
        'Expected one of (Bool, ListStart, MapStart, Null, String) '
        'but received EOF',
    )


def test_parse_error_token_expected():
    _assert_parse_error(
        '{True:,}',
        'Expected one of (Space) but received Comma\n\n'
        'Line 1, column 7\n\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '1   |{True:,}\n'
        '           ^\n',
    )
