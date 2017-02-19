# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from dumbconf._roundtrip import dumps_roundtrip
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


def test_deplace_nested_map_value_deeper():
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
