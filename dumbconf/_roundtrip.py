from __future__ import absolute_import
from __future__ import unicode_literals

import collections
import functools

from dumbconf import _primitive
from dumbconf import ast
from dumbconf._parse import parse
from dumbconf._parse import parse_from_tokens
from dumbconf._parse import unparse


# TODO: replace with six?
if str is bytes:  # pragma: no cover (PY2)
    text_type = unicode  # noqa
    int_types = (int, long)  # noqa
else:  # pragma: no cover (PY3)
    text_type = str
    int_types = (int,)


def _python_value(ast_obj):
    if isinstance(ast_obj, ast.PRIMITIVE):
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


def _to_tokens(val, indent=-1):
    if isinstance(val, text_type):
        return [ast.String(val=val, src=_primitive.String.dump(val))]
    elif isinstance(val, bool):
        return [ast.Bool(val=val, src=_primitive.Bool.dump(val))]
    elif val is None:
        return [ast.Null(val=None, src=_primitive.Null.dump(val))]
    elif isinstance(val, int_types):
        return [ast.Int(val=val, src=_primitive.Int.dump(val))]
    elif isinstance(val, float):
        return [ast.Float(val=val, src=_primitive.Float.dump(val))]
    elif isinstance(val, dict):
        return _map_tokens(val, indent)
    elif isinstance(val, (tuple, list)):
        return _list_tokens(val, indent)
    else:
        raise AssertionError('Unexpected value {!r}'.format(val))


def _inline(val, start, end, item_func, to_iter):
    ret = [start]
    if val:
        items = to_iter(val)
        ret.extend(item_func(items[0]))
        for item in items[1:]:
            ret.extend((ast.Comma(','), ast.Space(' ')))
            ret.extend(item_func(item))
    ret.append(end)
    return ret


def _multiline(val, indent, start, end, item_func, to_iter):
    ret = [start, ast.NL('\n')]
    for item in to_iter(val):
        ret.append(ast.Indent('    ' * (indent + 1)))
        ret.extend(item_func(item, indent + 1))
        ret.extend((ast.Comma(','), ast.NL('\n')))
    if indent > 0:
        ret.append(ast.Indent('    ' * indent))
    ret.append(end)
    return ret


def _container(val, indent, **kwargs):
    if indent >= 0:
        return _multiline(val, indent, **kwargs)
    else:
        return _inline(val, **kwargs)


def _map_item_tokens(kv, indent=-1):
    k, v = kv
    ret = []
    ret.extend(_to_tokens(k, indent))
    ret.extend((ast.Colon(':'), ast.Space(' ')))
    ret.extend(_to_tokens(v, indent))
    return ret


_map_tokens = functools.partial(
    _container,
    start=ast.MapStart('{'), end=ast.MapEnd('}'),
    item_func=_map_item_tokens, to_iter=lambda m: tuple(m.items()),
)
_list_tokens = functools.partial(
    _container,
    start=ast.ListStart('['), end=ast.ListEnd(']'),
    item_func=_to_tokens, to_iter=tuple,
)


def _to_ast(*args, **kwargs):
    # Run the parser to ensure a correct ast instead of building manually
    tokens = tuple(_to_tokens(*args, **kwargs)) + (ast.EOF(''),)
    return parse_from_tokens(tokens).val


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
    return obj._replace(val=_to_ast(new_value))


def _set_cb(obj, i, val):
    new_items = list(obj.val.items)
    new_items[i] = _replace_val(new_items[i], val)
    return new_items


def _set(obj, chain, val):
    if not chain:
        return _replace_val(obj, val)
    else:
        return _modify_items(obj, chain, _set_cb, val)


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


def _set_key_cb(obj, i, new_value):
    if not isinstance(obj.val, ast.Map):
        raise TypeError('Can only replace Map keys, not {}'.format(
            type(obj.val).__name__,
        ))
    key = _to_ast(new_value)
    if not isinstance(key, ast.PRIMITIVE):
        raise TypeError(
            'Keys must be of type ({}) but got {}'.format(
                ', '.join(tp.__name__ for tp in ast.PRIMITIVE),
                type(key).__name__,
            )
        )

    items = list(obj.val.items)
    items[i] = items[i]._replace(key=key)
    return items


def _set_key(obj, chain, new_value):
    return _modify_items(obj, chain, _set_key_cb, new_value)


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

    def replace_key(self, primitive):
        if not self.chain():
            raise TypeError('Index into a map to replace a key.')
        self.root = _set_key(self.root, self.chain(), primitive)

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


def load_roundtrip(stream):
    return loads_roundtrip(stream.read())


def dump_roundtrip(ast_proxy, stream):
    stream.write(dumps_roundtrip(ast_proxy))


def loads(s):
    return loads_roundtrip(s).python_value()


def dumps(v, indented=False):
    return unparse(_to_ast(v, indent=0 if indented else -1))


def load(stream):
    return loads(stream.read())


def dump(v, stream, indented=False):
    stream.write(dumps(v, indented=indented))
