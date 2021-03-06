from __future__ import absolute_import
from __future__ import unicode_literals

import collections


_ast_cls = collections.namedtuple


def _namesort(types):
    return tuple(sorted(types, key=lambda tp: tp.__name__))


def is_multiline(self):
    return len(self.head) > 1


def is_top_level_style(self):
    return not self.head


Doc = _ast_cls('Doc', ('head', 'val', 'tail'))

List = _ast_cls('List', ('head', 'items', 'tail'))
List.is_multiline = property(is_multiline)
List.is_top_level_style = property(is_top_level_style)
ListStart = _ast_cls('ListStart', ('src',))
ListEnd = _ast_cls('ListEnd', ('src',))
ListItem = _ast_cls('ListItem', ('head', 'val', 'tail'))

Map = _ast_cls('Map', ('head', 'items', 'tail'))
Map.is_multiline = property(is_multiline)
Map.is_top_level_style = property(is_top_level_style)
MapStart = _ast_cls('MapStart', ('src',))
MapEnd = _ast_cls('MapEnd', ('src',))
MapItem = _ast_cls('MapItem', ('head', 'key', 'inner', 'val', 'tail'))

Bool = _ast_cls('Bool', ('val', 'src'))
Null = _ast_cls('Null', ('val', 'src'))
Int = _ast_cls('Int', ('val', 'src'))
Float = _ast_cls('Float', ('val', 'src'))
String = _ast_cls('String', ('val', 'src'))
BareWordKey = _ast_cls('BareWordKey', ('val', 'src'))

Colon = _ast_cls('Colon', ('src',))
Comma = _ast_cls('Comma', ('src',))
Comment = _ast_cls('Comment', ('src',))
Indent = _ast_cls('Indent', ('src',))
NL = _ast_cls('NL', ('src',))
Space = _ast_cls('Space', ('src',))

EOF = _ast_cls('EOF', ('src',))

AST = _namesort(v for v in vars().values() if isinstance(v, type))
PRIMITIVE = _namesort(v for v in AST if v._fields == ('val', 'src'))
