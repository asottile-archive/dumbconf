# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pytest

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
