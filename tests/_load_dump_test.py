# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import collections

import pytest

from dumbconf._load_dump import loads


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('True', True),
        ('False', False),
        ('None', None),
        ("'ohai'", 'ohai'),
    ),
)
def test_loads_simple(s, expected):
    assert loads(s) == expected


def test_loads_list():
    src = '[True, False, "string"]'
    assert loads(src) == [True, False, 'string']


def test_loads_map():
    src = "{a: 'a_value', b: 'b_value', c: 'c_value'}"
    ret = loads(src)
    assert isinstance(ret, collections.OrderedDict)
    assert ret == {'a': 'a_value', 'b': 'b_value', 'c': 'c_value'}
