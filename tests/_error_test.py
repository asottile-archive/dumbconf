# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from dumbconf._error import ParseError


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
