# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

from dumbconf import ast
from dumbconf._error import ParseError
from dumbconf._tokenize import tokenize


def _assert_tokenize_error(src, s):
    with pytest.raises(ParseError) as excinfo:
        tokenize(src)
    assert str(excinfo.value) == s


def test_tokenize_error_unexpected_token():
    _assert_tokenize_error(
        '&',
        'Unexpected token\n\n'
        'Line 1, column 1\n\n'
        'Line|Source\n'
        '----|------------------------------------------------------\n'
        '1   |&\n'
        '     ^\n',
    )


def test_bare_word_key_starts_with_other_token():
    tokens = tokenize('{true_values: []}')
    assert tokens == (
        ast.MapStart('{'),
        ast.BareWordKey('true_values', 'true_values'),
        ast.Colon(':'), ast.Space(' '),
        ast.ListStart('['), ast.ListEnd(']'),
        ast.MapEnd('}'),
        ast.EOF(''),
    )
