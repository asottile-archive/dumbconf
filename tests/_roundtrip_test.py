# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import collections
import io

import pytest

from dumbconf._roundtrip import dump
from dumbconf._roundtrip import dump_roundtrip
from dumbconf._roundtrip import dumps
from dumbconf._roundtrip import dumps_roundtrip
from dumbconf._roundtrip import load
from dumbconf._roundtrip import load_roundtrip
from dumbconf._roundtrip import loads
from dumbconf._roundtrip import loads_roundtrip


def test_replace_value_same_type():
    val = loads_roundtrip('True  # comment')
    val.replace_value(False)
    ret = dumps_roundtrip(val)
    assert ret == 'False  # comment'


def test_replace_value_new_type():
    val = loads_roundtrip('True  # comment')
    val.replace_value(None)
    ret = dumps_roundtrip(val)
    assert ret == 'None  # comment'


def test_replace_string():
    val = loads_roundtrip('True  # comment')
    val.replace_value('ohai')
    ret = dumps_roundtrip(val)
    assert ret == "'ohai'  # comment"


def test_replace_int():
    val = loads_roundtrip('True  # comment')
    val.replace_value(5)
    ret = dumps_roundtrip(val)
    assert ret == '5  # comment'


def test_replace_float():
    val = loads_roundtrip('True  # comment')
    val.replace_value(5.)
    ret = dumps_roundtrip(val)
    assert ret == '5.0  # comment'


def test_replace_key():
    val = loads_roundtrip("{k: 'v'}")
    val['k'].replace_key('new key!')
    ret = dumps_roundtrip(val)
    assert ret == "{'new key!': 'v'}"


def test_replace_key_at_root():
    val = loads_roundtrip('{True: False}')
    with pytest.raises(TypeError) as excinfo:
        val.replace_key('new key')
    assert excinfo.value.args == ('Index into a map to replace a key.',)


def test_replace_key_not_a_map():
    val = loads_roundtrip('[1, 2, 3]')
    with pytest.raises(TypeError) as excinfo:
        val[0].replace_key('new key')
    assert excinfo.value.args == ('Can only replace Map keys, not List',)


def test_replace_key_illegal_type():
    val = loads_roundtrip('{True: False}')
    with pytest.raises(TypeError) as excinfo:
        val[True].replace_key([1, 2, 3])
    assert excinfo.value.args == (
        'Keys must be of type (BareWordKey, Bool, Float, Int, Null, String) '
        'but got List',
    )


def test_replace_map_value_top_level():
    val = loads_roundtrip(
        '{\n'
        '    a: True,  # comment\n'
        '    b: False,  # comment\n'
        '}\n'
    )
    val['b'] = None
    ret = dumps_roundtrip(val)
    assert ret == (
        '{\n'
        '    a: True,  # comment\n'
        '    b: None,  # comment\n'
        '}\n'
    )


def test_replace_list_value_top_level():
    val = loads_roundtrip(
        '[\n'
        '    True,  # comment\n'
        '    False,  # comment\n'
        ']\n'
    )
    val[0] = None
    ret = dumps_roundtrip(val)
    assert ret == (
        '[\n'
        '    None,  # comment\n'
        '    False,  # comment\n'
        ']\n'
    )


def test_replace_nested_map_value():
    val = loads_roundtrip(
        '{\n'
        '    a: {\n'
        '        b: True,  # comment\n'
        '    },\n'
        '}\n'
    )
    val['a']['b'] = None
    ret = dumps_roundtrip(val)
    assert ret == (
        '{\n'
        '    a: {\n'
        '        b: None,  # comment\n'
        '    },\n'
        '}\n'
    )


def test_replace_nested_map_value_deeper():
    val = loads_roundtrip('{a: {b: {c: True}}}')
    val['a']['b']['c'] = False
    ret = dumps_roundtrip(val)
    assert ret == '{a: {b: {c: False}}}'


def test_delete_dictionary_key():
    val = loads_roundtrip(
        '{\n'
        '    # comment documenting a\n'
        '    a: True,  # comment\n'
        '    # comment documenting b\n'
        '    b: False,  # comment\n'
        '}\n'
    )
    del val['a']
    ret = dumps_roundtrip(val)
    assert ret == (
        '{\n'
        '    # comment documenting b\n'
        '    b: False,  # comment\n'
        '}\n'
    )


def test_delete_nested():
    val = loads_roundtrip(
        '{\n'
        '    a: {\n'
        '        b: True,\n'
        '        c: True,\n'
        '    },\n'
        '}\n'
    )
    del val['a']['b']
    ret = dumps_roundtrip(val)
    assert ret == (
        '{\n'
        '    a: {\n'
        '        c: True,\n'
        '    },\n'
        '}\n'
    )


def test_delete_nested_fixup_trailing_comma_inline():
    val = loads_roundtrip('{a: {b: {c: True, d: False}}}')
    del val['a']['b']['d']
    ret = dumps_roundtrip(val)
    assert ret == '{a: {b: {c: True}}}'


def test_delete_fixup_trailing_space_multiline():
    val = loads_roundtrip(
        '[\n'
        '    True, False,\n'
        ']'
    )
    del val[1]
    ret = dumps_roundtrip(val)
    assert ret == (
        '[\n'
        '    True,\n'
        ']'
    )


def test_delete_fixup_indent():
    val = loads_roundtrip(
        '[\n'
        '    True, False,\n'
        ']'
    )
    del val[0]
    ret = dumps_roundtrip(val)
    assert ret == (
        '[\n'
        '    False,\n'
        ']'
    )


def test_nested_python_value():
    val = loads_roundtrip(
        '{\n'
        '    True: {\n'
        '        False: False,\n'
        '        True: True,\n'
        '    },\n'
        '}'
    )
    assert val[True][False].python_value() is False
    assert val[True][True].python_value() is True


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('True', True),
        ('False', False),
        ('None', None),
        ("'ohai'", 'ohai'),
        ('5', 5),
        ('5.', 5.),
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


@pytest.mark.parametrize(
    ('v', 'expected'),
    (
        (True, 'True'),
        (False, 'False'),
        (None, 'None'),
        ('ohai', "'ohai'"),
        (5, '5'),
        (5.1, '5.1'),
        ((), '[]'),
        ([], '[]'),
        ({}, '{}'),
    ),
)
def test_dumps_simple(v, expected):
    assert dumps(v) == expected


def test_dumps_list():
    assert dumps([1, 2, 3]) == '[1, 2, 3]'


def test_dumps_list_indented():
    ret = dumps([1, 2, 3], indented=True)
    assert ret == (
        '[\n'
        '    1,\n'
        '    2,\n'
        '    3,\n'
        ']'
    )


def test_dumps_nested_list_indented():
    ret = dumps([[1, 2], [3, 4]], indented=True)
    assert ret == (
        '[\n'
        '    [\n'
        '        1,\n'
        '        2,\n'
        '    ],\n'
        '    [\n'
        '        3,\n'
        '        4,\n'
        '    ],\n'
        ']'
    )


def test_dumps_map():
    assert dumps({1: 2, 3: 4}) == '{1: 2, 3: 4}'


def test_dumps_map_indented():
    ret = dumps({1: 2, 3: 4}, indented=True)
    assert ret == (
        '{\n'
        '    1: 2,\n'
        '    3: 4,\n'
        '}'
    )


def test_dumps_nested_map_indented():
    ret = dumps({1: {2: 3}, 4: {5: 6}}, indented=True)
    assert ret == (
        '{\n'
        '    1: {\n'
        '        2: 3,\n'
        '    },\n'
        '    4: {\n'
        '        5: 6,\n'
        '    },\n'
        '}'
    )


def test_load():
    sio = io.StringIO('{hello: "world"}')
    assert load(sio) == {'hello': 'world'}


def test_dump():
    sio = io.StringIO()
    dump({'hello': 'world'}, sio)
    assert sio.getvalue() == "{'hello': 'world'}"


def test_load_dump_roundtrip():
    s = (
        '{\n'
        '    True: False,  # comment\n'
        '}'
    )
    sio = io.StringIO(s)
    assert dumps_roundtrip(load_roundtrip(sio)) == s


def test_dump_roundtrip():
    s = (
        '{\n'
        '    True: False,  # comment\n'
        '}'
    )
    sio = io.StringIO()
    dump_roundtrip(loads_roundtrip(s), sio)
    assert sio.getvalue() == s
