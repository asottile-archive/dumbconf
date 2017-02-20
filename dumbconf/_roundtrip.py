from __future__ import absolute_import
from __future__ import unicode_literals

from dumbconf import _primitive
from dumbconf import ast
from dumbconf._parse import parse
from dumbconf._parse import unparse


# TODO: replace with six?
if str is bytes:  # pragma: no cover (PY2)
    text_type = unicode  # noqa
else:  # pragma: no cover (PY3)
    text_type = str


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
    else:
        raise AssertionError('Unexpected value {!r}'.format(new_value))
    attrs = ast_obj._asdict()
    attrs['val'] = new_value
    attrs['src'] = to_src(new_value)
    return new_cls(**attrs)


def _replace_val(obj, new_value):
    return obj._replace(val=_merge_primitive(obj.val, new_value))


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


def _replace_index(obj, new_value, index_chain):
    if not index_chain:
        return _replace_val(obj, new_value)
    else:
        key, rest = index_chain[0], index_chain[1:]
        i = _key_index(obj.val, key)

        new_items = list(obj.val.items)
        new_items[i] = _replace_index(obj.val.items[i], new_value, rest)
        return obj._replace(val=obj.val._replace(items=tuple(new_items)))


def _delete_index(obj, index_chain):
    key, rest = index_chain[0], index_chain[1:]
    i = _key_index(obj.val, key)

    orig_item = obj.val.items[i]
    new_items = list(obj.val.items)

    if not rest:
        del new_items[i]

        # If we're deleting the last item of an inline container, we need to
        # remove the comma from the new last item
        if not obj.val.is_multiline and len(obj.val.items) == i + 1:
            new_items[-1] = new_items[-1]._replace(tail=())
        # If we're deleting an element of a non-inline container we may need
        # to adjust the item before (to change ', ' to ',\n')
        elif (
                obj.val.is_multiline and
                i - 1 >= 0 and
                orig_item.head == () and
                orig_item.tail[-1].src.endswith('\n')
        ):
            new_items[i - 1] = new_items[i - 1]._replace(tail=orig_item.tail)
        # If we're deleting an element of a non-inlienc container we may need
        # to adjust the item after (to change head to an indent)
        elif (
                obj.val.is_multiline and
                i + 1 < len(obj.val.items) and
                orig_item.head != () and
                not orig_item.tail[-1].src.endswith('\n')
        ):
            new_items[i] = new_items[i]._replace(head=orig_item.head)
    else:
        new_items[i] = _delete_index(orig_item, rest)
    return obj._replace(val=obj.val._replace(items=tuple(new_items)))


class AstProxyChain(object):
    def __init__(self, ast_proxy, chain):
        self._ast_proxy = ast_proxy
        self._chain = chain

    def __setitem__(self, key, primitive):
        self._ast_proxy._ast_obj = _replace_index(
            self._ast_proxy._ast_obj, primitive, self._chain + (key,)
        )

    def __delitem__(self, key):
        self._ast_proxy._ast_obj = _delete_index(
            self._ast_proxy._ast_obj, self._chain + (key,)
        )

    def __getitem__(self, key):
        return AstProxyChain(self._ast_proxy, self._chain + (key,))

    def replace_value(self, primitive):
        self._ast_proxy._ast_obj = _replace_index(
            self._ast_proxy._ast_obj, primitive, self._chain,
        )


class AstProxy(AstProxyChain):
    """The base case for our ast proxy"""

    def __init__(self, ast_obj):
        super(AstProxy, self).__init__(self, ())
        self._ast_obj = ast_obj


def loads_roundtrip(s):
    return AstProxy(parse(s))


def dumps_roundtrip(ast_proxy):
    return unparse(ast_proxy._ast_obj)
