# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from dumbconf import ast
from dumbconf._error import ParseError
from dumbconf._parse import debug
from dumbconf._parse import parse as parse_actual
from dumbconf._parse import unparse


EXPECT_VAL = (
    'Expected one of (Bool, Float, Int, ListStart, MapStart, Null, String) '
)


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
    ret = debug(parse('[true]'))
    assert ret == (
        'Doc(\n'
        '    head=(),\n'
        '    val=List(\n'
        '        head=(\n'
        "            ListStart(src={!r}),\n"
        '        ),\n'
        '        items=(\n'
        '            ListItem(\n'
        '                head=(),\n'
        "                val=Bool(val=True, src={!r}),\n"
        '                tail=(),\n'
        '            ),\n'
        '        ),\n'
        '        tail=(\n'
        "            ListEnd(src={!r}),\n"
        '        ),\n'
        '    ),\n'
        '    tail=(),\n'
        ')'.format('[', 'true', ']')
    )


@pytest.mark.parametrize(
    ('s', 'expected_val'),
    (('true', True), ('false', False)),
)
def test_parse_boolean(s, expected_val):
    expected = ast.Doc(
        head=(), val=ast.Bool(val=expected_val, src=s), tail=(),
    )
    assert parse(s) == expected


def test_parse_null():
    expected = ast.Doc(head=(), val=ast.Null(None, src='null'), tail=())
    assert parse('null') == expected


@pytest.mark.parametrize(
    ('s', 'expected_val'),
    (
        ('0x15', 0x15),
        ('0b101', 0b101),
        ('0o755', 0o755),
        ('1234', 1234),
        ('0', 0),
        ('-5', -5),
    ),
)
def test_parse_integer(s, expected_val):
    ret = parse(s)
    expected = ast.Doc(head=(), val=ast.Int(expected_val, src=s), tail=())
    assert ret == expected


@pytest.mark.parametrize(
    ('s', 'expected_val'),
    (
        ('1e5', 1e5),
        ('1.', 1.),
        ('.5', .5),
        ('0.5', 0.5),
        ('6.02e23', 6.02e23),
        ('-314e-2', -314e-2),
    ),
)
def test_parse_float(s, expected_val):
    ret = parse(s)
    expected = ast.Doc(head=(), val=ast.Float(expected_val, src=s), tail=())
    assert ret == expected


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


def test_trivial_list():
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
    assert not ret.val.is_multiline
    assert not ret.val.is_top_level_style


def test_list_one_value_inline():
    ret = parse('[true]')
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['),),
            items=(
                ast.ListItem(
                    head=(), val=ast.Bool(val=True, src='true'), tail=(),
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_list_several_values_inline():
    ret = parse('[true, false]')
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['),),
            items=(
                ast.ListItem(
                    head=(),
                    val=ast.Bool(val=True, src='true'),
                    tail=(ast.Comma(','), ast.Space(' ')),
                ),
                ast.ListItem(
                    head=(),
                    val=ast.Bool(val=False, src='false'),
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
        '[truefalse]',
        'Expected one of (Comma) but received Bool\n\n'
        'Line 1, column 6\n\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '1   |[truefalse]\n'
        '          ^\n',
    )


def test_list_multiline_trivial():
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
    assert ret.val.is_multiline
    assert not ret.val.is_top_level_style


def test_list_multiline_comments():
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


def test_list_multiline():
    ret = parse(
        '[\n'
        '    true,\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(
                ast.ListItem(
                    head=(ast.Indent('    '),),
                    val=ast.Bool(val=True, src='true'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_list_multiline_comment_before():
    ret = parse(
        '[\n'
        '    # Hello\n'
        '    true,\n'
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
                    val=ast.Bool(val=True, src='true'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_list_multiline_comment_after():
    ret = parse(
        '[\n'
        '    true,\n'
        '    # Comment\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(
                ast.ListItem(
                    head=(ast.Indent('    '),),
                    val=ast.Bool(val=True, src='true'),
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


def test_list_multiple_items_multiline():
    ret = parse(
        '[\n'
        '    true,\n'
        '    false,\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(
                ast.ListItem(
                    head=(ast.Indent('    '),),
                    val=ast.Bool(val=True, src='true'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
                ast.ListItem(
                    head=(ast.Indent('    '),),
                    val=ast.Bool(val=False, src='false'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_list_multiline_multiple_items_on_one_line():
    ret = parse(
        '[\n'
        '    true, false,\n'
        '    false, true,\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(
                ast.ListItem(
                    head=(ast.Indent('    '),),
                    val=ast.Bool(val=True, src='true'),
                    tail=(ast.Comma(','), ast.Space(' ')),
                ),
                ast.ListItem(
                    head=(),
                    val=ast.Bool(val=False, src='false'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
                ast.ListItem(
                    head=(ast.Indent('    '),),
                    val=ast.Bool(val=False, src='false'),
                    tail=(ast.Comma(','), ast.Space(' ')),
                ),
                ast.ListItem(
                    head=(),
                    val=ast.Bool(val=True, src='true'),
                    tail=(ast.Comma(','), ast.NL('\n')),
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_nested_list():
    ret = parse(
        '[\n'
        '    [\n'
        '        1,\n'
        '    ],\n'
        ']'
    )
    expected = ast.Doc(
        head=(),
        val=ast.List(
            head=(ast.ListStart('['), ast.NL('\n')),
            items=(
                ast.ListItem(
                    head=(ast.Indent('    '),),
                    val=ast.List(
                        head=(ast.ListStart('['), ast.NL('\n')),
                        items=(
                            ast.ListItem(
                                head=(ast.Indent('        '),),
                                val=ast.Int(val=1, src='1'),
                                tail=(ast.Comma(','), ast.NL('\n')),
                            ),
                        ),
                        tail=(ast.Indent('    '), ast.ListEnd(']')),
                    ),
                    tail=(ast.Comma(','), ast.NL('\n'))
                ),
            ),
            tail=(ast.ListEnd(']'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_regression_multiline_trailing_space():
    _assert_parse_error(
        '[\n'
        '    true, \n'
        ']',
        EXPECT_VAL + 'but received NL\n\n'
        'Line 2, column 11\n\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '1   |[\n'
        '2   |    true, \n'
        '               ^\n'
        '3   |]\n',
    )


def test_map_trivial():
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
    assert not ret.val.is_multiline
    assert not ret.val.is_top_level_style


def test_map_one_element_inline():
    ret = parse('{true: false}')
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(ast.MapStart('{'),),
            items=(
                ast.MapItem(
                    head=(),
                    key=ast.Bool(val=True, src='true'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=False, src='false'),
                    tail=(),
                ),
            ),
            tail=(ast.MapEnd('}'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_map_multiple_elements_inline():
    ret = parse('{true: false, false: true}')
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(ast.MapStart('{'),),
            items=(
                ast.MapItem(
                    head=(),
                    key=ast.Bool(val=True, src='true'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=False, src='false'),
                    tail=(ast.Comma(','), ast.Space(' ')),
                ),
                ast.MapItem(
                    head=(),
                    key=ast.Bool(val=False, src='false'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=True, src='true'),
                    tail=(),
                ),
            ),
            tail=(ast.MapEnd('}'),),
        ),
        tail=(),
    )
    assert ret == expected


def test_map_multiline_trivial():
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
    assert ret.val.is_multiline
    assert not ret.val.is_top_level_style


def test_map_multiline_one_element():
    ret = parse(
        '{\n'
        '    true: false,\n'
        '}'
    )
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(ast.MapStart('{'), ast.NL('\n')),
            items=(
                ast.MapItem(
                    head=(ast.Indent('    '),),
                    key=ast.Bool(val=True, src='true'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=False, src='false'),
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
        '    true: false,\n'
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
                    key=ast.Bool(val=True, src='true'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=False, src='false'),
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


def test_top_level_map():
    ret = parse(
        'true: false\n'
        'false: true'
    )
    expected = ast.Doc(
        head=(),
        val=ast.Map(
            head=(),
            items=(
                ast.MapItem(
                    head=(),
                    key=ast.Bool(val=True, src='true'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=False, src='false'),
                    tail=(ast.NL('\n'),),
                ),
                ast.MapItem(
                    head=(),
                    key=ast.Bool(val=False, src='false'),
                    inner=(ast.Colon(':'), ast.Space(' ')),
                    val=ast.Bool(val=True, src='true'),
                    tail=(),
                ),
            ),
            tail=(),
        ),
        tail=(),
    )
    assert ret == expected
    assert ret.val.is_top_level_style


def test_file_starting_in_ws():
    ret = parse('\n\ntrue')
    expected = ast.Doc(
        head=(ast.NL('\n'), ast.NL('\n')),
        val=ast.Bool(val=True, src='true'),
        tail=(),
    )
    assert ret == expected


def test_file_ending_in_ws():
    ret = parse('true\n')
    expected = ast.Doc(
        head=(), val=ast.Bool(val=True, src='true'), tail=(ast.NL('\n'),),
    )
    assert ret == expected


def test_file_starting_with_comments():
    ret = parse('# hello\ntrue')
    expected = ast.Doc(
        head=(ast.Comment('# hello\n'),),
        val=ast.Bool(val=True, src='true'),
        tail=(),
    )
    assert ret == expected


def test_file_ending_in_comment():
    ret = parse('true # ohai\n')
    expected = ast.Doc(
        head=(),
        val=ast.Bool(val=True, src='true'),
        tail=(ast.Space(' '), ast.Comment('# ohai\n')),
    )
    assert ret == expected


def test_file_ending_in_comment_no_nl():
    ret = parse('true # ohai')
    expected = ast.Doc(
        head=(),
        val=ast.Bool(val=True, src='true'),
        tail=(ast.Space(' '), ast.Comment('# ohai')),
    )
    assert ret == expected


def test_file_ending_in_several_comments():
    ret = parse('true\n# hello\n# there\n')
    expected = ast.Doc(
        head=(),
        val=ast.Bool(val=True, src='true'),
        tail=(
            ast.NL('\n'), ast.Comment('# hello\n'), ast.Comment('# there\n'),
        ),
    )
    assert ret == expected


def test_parse_error_no_contents():
    _assert_parse_error('', EXPECT_VAL + 'but received EOF')


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
