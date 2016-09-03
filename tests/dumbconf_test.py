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


def test_file_starting_in_ws():
    ret = parse('\n\nTrue')
    expected = ast.Doc(
        head=(ast.WS('\n\n'),), body=ast.Bool(val=True, src='True'), tail=(),
    )
    assert ret == expected


def test_file_ending_in_ws():
    ret = parse('True\n')
    expected = ast.Doc(
        head=(), body=ast.Bool(val=True, src='True'), tail=(ast.WS('\n'),),
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
        tail=(ast.WS(' '), ast.Comment('# ohai\n')),
    )
    assert ret == expected


def test_file_ending_in_comment_no_nl():
    ret = parse('True # ohai')
    expected = ast.Doc(
        head=(),
        body=ast.Bool(val=True, src='True'),
        tail=(ast.WS(' '), ast.Comment('# ohai')),
    )
    assert ret == expected


def test_file_ending_in_several_comments():
    ret = parse('True\n# hello\n# there\n')
    expected = ast.Doc(
        head=(),
        body=ast.Bool(val=True, src='True'),
        tail=(
            ast.WS('\n'), ast.Comment('# hello\n'), ast.Comment('# there\n'),
        ),
    )
    assert ret == expected
