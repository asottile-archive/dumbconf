from __future__ import absolute_import
from __future__ import unicode_literals

import collections
import functools

from dumbconf import _primitive
from dumbconf import ast
from dumbconf._parse import parse
from dumbconf._parse import unparse


# TODO: replace with six?
if str is bytes:  # pragma: no cover (PY2)
    text_type = unicode  # noqa
    int_types = (int, long)  # noqa
else:  # pragma: no cover (PY3)
    text_type = str
    int_types = (int,)


def _python_value(ast_obj):
    if isinstance(ast_obj, ast.Primitive):
        return ast_obj.val
    elif isinstance(ast_obj, ast.List):
        return [_python_value(item.val) for item in ast_obj.items]
    elif isinstance(ast_obj, ast.Map):
        return collections.OrderedDict(
            (_python_value(item.key), _python_value(item.val))
            for item in ast_obj.items
        )
    else:
        raise AssertionError('Unknown ast: {!r}'.format(ast_obj))


def _merge_primitive(ast_obj, new_value):
    if isinstance(new_value, text_type):
        new_cls = ast.String
        to_src = _primitive.String.dump
    elif isinstance(new_value, bool):
        new_cls = ast.Bool
        to_src = _primitive.Bool.dump
    elif new_value is None:
        new_cls = ast.Null
        to_src = _primitive.Null.dump
    elif isinstance(new_value, int_types):
        new_cls = ast.Int
        to_src = _primitive.Int.dump
    elif isinstance(new_value, float):
        new_cls = ast.Float
        to_src = _primitive.Float.dump
    else:
        raise AssertionError('Unexpected value {!r}'.format(new_value))
    attrs = ast_obj._asdict()
    attrs['val'] = new_value
    attrs['src'] = to_src(new_value)
    return new_cls(**attrs)


def _key_index(val, key):
    if isinstance(val, ast.Map):
        for i, item in enumerate(val.items):
            if item.key.val == key:
                return i
        else:
            raise AssertionError('TODO: KeyError(key)')
    elif isinstance(val, ast.List):
        return key
    else:
        raise AssertionError('{!r}: not indexable'.format(val))


def _get(obj, chain):
    if not chain:
        return obj
    else:
        key, rest = chain[0], chain[1:]
        i = _key_index(obj.val, key)
        target = obj.val.items[i]
        if not rest:
            return target
        else:
            return _get(target, rest)


def _modify_items(obj, chain, items_cb, *args):
    key, rest = chain[0], chain[1:]
    i = _key_index(obj.val, key)

    if not rest:
        new_items = items_cb(obj, i, *args)
    else:
        new_items = list(obj.val.items)
        new_items[i] = _modify_items(new_items[i], rest, items_cb, *args)
    return obj._replace(val=obj.val._replace(items=tuple(new_items)))


def _replace_val(obj, new_value):
    return obj._replace(val=_merge_primitive(obj.val, new_value))


def _set_cb(obj, i, val):
    new_items = list(obj.val.items)
    new_items[i] = _replace_val(new_items[i], val)
    return new_items


def _set(obj, chain, new_value):
    if not chain:
        return _replace_val(obj, new_value)
    else:
        return _modify_items(obj, chain, _set_cb, new_value)


def _delete_cb(obj, i):
    orig_item = obj.val.items[i]
    new_items = list(obj.val.items)
    del new_items[i]

    # If we're deleting the last item of an inline container, we need to
    # remove the comma from the new last item
    if not obj.val.is_multiline and len(obj.val.items) == i + 1:
        new_items[-1] = new_items[-1]._replace(tail=())
    # If we're deleting an element of a non-inline container we may need to
    # adjust the item before (to change ', ' to ',\n')
    elif (
            obj.val.is_multiline and
            i - 1 >= 0 and
            orig_item.head == () and
            orig_item.tail[-1].src.endswith('\n')
    ):
        new_items[i - 1] = new_items[i - 1]._replace(tail=orig_item.tail)
    # If we're deleting an element of a non-inline container we may need to
    # adjust the item after (to change head to an indent)
    elif (
            obj.val.is_multiline and
            i + 1 < len(obj.val.items) and
            orig_item.head != () and
            not orig_item.tail[-1].src.endswith('\n')
    ):
        new_items[i] = new_items[i]._replace(head=orig_item.head)
    return new_items


_delete = functools.partial(_modify_items, items_cb=_delete_cb)


class AstProxyChain(object):
    def __init__(self, ast_proxy, chain):
        self._ast_proxy = ast_proxy
        self._chain = chain

    def __setitem__(self, key, primitive):
        self.root = _set(self.root, self.chain(key), primitive)

    def __delitem__(self, key):
        self.root = _delete(self.root, self.chain(key))

    def __getitem__(self, key):
        return AstProxyChain(self._ast_proxy, self.chain(key))

    @property
    def root(self):
        return self._ast_proxy._ast_obj

    @root.setter
    def root(self, val):
        self._ast_proxy._ast_obj = val

    def chain(self, *args):
        return self._chain + args

    def replace_value(self, primitive):
        self.root = _set(self.root, self.chain(), primitive)

    def python_value(self):
        return _python_value(_get(self.root, self.chain()).val)


class AstProxy(AstProxyChain):
    """The base case for our ast proxy"""

    def __init__(self, ast_obj):
        super(AstProxy, self).__init__(self, ())
        self._ast_obj = ast_obj


def loads_roundtrip(s):
    return AstProxy(parse(s))


def dumps_roundtrip(ast_proxy):
    return unparse(ast_proxy._ast_obj)


def loads(s):
    return loads_roundtrip(s).python_value()
