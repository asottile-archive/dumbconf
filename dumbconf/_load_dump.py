from __future__ import absolute_import
from __future__ import unicode_literals

import collections

from dumbconf import ast
from dumbconf._parse import parse


def _to_python_value(ast_obj):
    if isinstance(ast_obj, ast.Doc):
        return _to_python_value(ast_obj.val)
    elif isinstance(
            ast_obj, (ast.BareWordKey, ast.Bool, ast.Null, ast.String),
    ):
        return ast_obj.val
    elif isinstance(ast_obj, ast.List):
        return [_to_python_value(item.val) for item in ast_obj.items]
    elif isinstance(ast_obj, ast.Map):
        return collections.OrderedDict(
            (_to_python_value(item.key), _to_python_value(item.val))
            for item in ast_obj.items
        )
    else:
        raise AssertionError('Unknown ast: {!r}'.format(ast_obj))


def loads(s):
    return _to_python_value(parse(s))
